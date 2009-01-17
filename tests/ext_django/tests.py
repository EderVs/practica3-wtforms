#!/usr/bin/env python
"""
    ext_django.tests
    ~~~~~~~~~~~~~~~~
    
    Unittests for wtforms.ext.django
    
    :copyright: 2009 by James Crasta, Thomas Johansson.
    :license: MIT, see LICENSE.txt for details.
"""

import sys, os
TESTS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, TESTS_DIR)

##########################################################################
# -- Django Initialization
# 
# Unfortunately, we cannot do this in the setUp for a test case, as the
# settings.configure method cannot be called more than once, and we cannot
# control the order in which tests are run, so making a throwaway test won't
# work either.

from django.conf import settings
settings.configure(INSTALLED_APPS=['ext_django', 'wtforms.ext.django'], DATABASE_ENGINE='sqlite3', TEST_DATABASE_NAME=':memory:')

from django.db import connection
connection.creation.create_test_db(verbosity=0)

# -- End hacky Django initialization

from django.template import Context, Template
from django.test import TestCase as DjangoTestCase
from ext_django import models as test_models 
from unittest import TestCase
from wtforms import Form, fields, validators
from wtforms.ext.django.orm import model_form
from wtforms.ext.django.fields import QuerySetSelectField, ModelSelectField

def validator_names(field):
    return [x.func_name for x in field.validators]

class DummyPostData(dict):
    def getlist(self, key):
        return self[key]

class TemplateTagsTest(TestCase):
    TEST_TEMPLATE = """{% load wtforms %}
    {% autoescape off %}{{ form.a }}{% endautoescape %}
    {% form_field form.a %}
    {% for field in form %}{% form_field field class=someclass onclick="alert()" %}
    {% endfor %}
    """

    TEMPLATE_EXPECTED_OUTPUT = """
    <input id="a" name="a" type="text" value="" />
    <input id="a" name="a" type="text" value="" />
    <input class="CLASSVAL!" id="a" name="a" onclick="alert()" type="text" value="" />
    <select class="CLASSVAL!" id="b" name="b" onclick="alert()"><option value="a">hi</option><option value="b">bai</option></select>
    """
    class F(Form):
        a = fields.TextField()
        b = fields.SelectField(choices=[('a', 'hi'), ('b', 'bai')])

    def test_form_field(self):
        t = Template(self.TEST_TEMPLATE)
        output = t.render(Context({'form': self.F(), 'someclass': "CLASSVAL!"}))
        self.assertEqual(output.strip(), self.TEMPLATE_EXPECTED_OUTPUT.strip())

class ModelFormTest(TestCase):
    F = model_form(test_models.User)
    form = F()
    form_with_pk = model_form(test_models.User, include_pk=True)()

    def test_form_sanity(self):
        self.assertEqual(self.F.__name__, 'UserForm')
        self.assertEqual(len([x for x in self.form]), 13) 
        self.assertEqual(len([x for x in self.form_with_pk]), 14) 

    def test_label(self):
        self.assertEqual(self.form.reg_ip.label.text, 'IP Addy')
        self.assertEqual(self.form.posts.label.text, 'posts')

    def test_description(self):
        self.assertEqual(self.form.birthday.description, 'Teh Birthday')

    def test_max_length(self):
        self.assertTrue('_length' in validator_names(self.form.username))
        self.assertTrue('_length' not in validator_names(self.form.posts))

    def test_optional(self):
        self.assertTrue('_optional' in validator_names(self.form.email))

    def test_simple_fields(self):
        self.assertEqual(type(self.form.file), fields.FileField)
        self.assertEqual(type(self.form.file2), fields.FileField)
        self.assertEqual(type(self.form_with_pk.id), fields.IntegerField)
        self.assertEqual(type(self.form.slug), fields.TextField)

    def test_custom_converters(self):
        self.assertEqual(type(self.form.email), fields.TextField)
        self.assertTrue('_email' in validator_names(self.form.email))
        self.assertEqual(type(self.form.reg_ip), fields.TextField)
        self.assertTrue('_ip_address' in validator_names(self.form.reg_ip))

    def test_us_states(self):
        self.assertTrue(len(self.form.state.choices) >= 50)

class QuerySetSelectFieldTest(DjangoTestCase):
    fixtures = ['ext_django.json']

    def setUp(self):
        from django.core.management import call_command
        self.queryset = test_models.Group.objects.all()
        class F(Form):
            a = QuerySetSelectField(allow_blank=True, label_attr='name')
            b = QuerySetSelectField(queryset=self.queryset)

        self.F = F

    def test_queryset_freshness(self):
        form = self.F()
        self.assertTrue(form.b.queryset is not self.queryset)

    def test_with_data(self):
        form = self.F()
        form.a.queryset = self.queryset[1:]
        self.assertEqual(form.a(), u'''<select id="a" name="a"><option selected="selected" value="__None"></option><option value="2">Admins</option></select>''')
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.validate(form), True)
        self.assertEqual(form.b.validate(form), False)
        form.b.data = test_models.Group.objects.get(pk=1)
        self.assertEqual(form.b.validate(form), True)
        self.assertEqual(form.b(), u'''<select id="b" name="b"><option selected="selected" value="1">1: Users</option><option value="2">2: Admins</option></select>''')

    def test_formdata(self):
        form = self.F(DummyPostData(a=['1'], b=['3']))
        form.a.queryset = self.queryset[1:]
        self.assertEqual(form.a.data, None)
        self.assertEqual(form.a.validate(form), True)
        self.assertEqual(form.b.data, None)
        self.assertEqual(form.b.validate(form), False)
        form = self.F(DummyPostData(b=[2]))
        self.assertEqual(form.b.data.pk, 2)
        self.assertEqual(form.b.validate(form), True)
        

class ModelSelectFieldTest(DjangoTestCase):
    fixtures = ['ext_django.json']

    class F(Form):
        a = ModelSelectField(model=test_models.Group)

    def test(self):
        form = self.F()
        self.assertEqual(form.a(), u'''<select id="a" name="a"><option value="1">1: Users</option><option value="2">2: Admins</option></select>''')

        
if __name__ == '__main__':
    import unittest
    unittest.main()