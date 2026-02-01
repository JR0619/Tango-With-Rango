#
# Tango with Django 2 Progress Tests (Patched for Django 2.2)
# By Leif Azzopardi and David Maxwell
# Patched by Copilot for Django 2.2 admin HTML compatibility
#

import os
import warnings
from rango.models import Category, Page
from django.urls import reverse
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User

FAILURE_HEADER = f"{os.linesep}{os.linesep}{os.linesep}================{os.linesep}TwD TEST FAILURE =({os.linesep}================{os.linesep}"
FAILURE_FOOTER = f"{os.linesep}"


class Chapter5DatabaseConfigurationTests(TestCase):
    def does_gitignore_include_database(self, path):
        f = open(path, 'r')
        for line in f:
            if line.strip().startswith('db.sqlite3'):
                return True
        f.close()
        return False

    def test_databases_variable_exists(self):
        self.assertTrue(settings.DATABASES, f"{FAILURE_HEADER}Your project's settings module does not have a DATABASES variable.{FAILURE_FOOTER}")
        self.assertTrue('default' in settings.DATABASES, f"{FAILURE_HEADER}You do not have a 'default' database configuration.{FAILURE_FOOTER}")

    def test_gitignore_for_database(self):
        git_base_dir = os.popen('git rev-parse --show-toplevel').read().strip()
        if git_base_dir.startswith('fatal'):
            warnings.warn("Not using Git. Skipping test.")
        else:
            gitignore_path = os.path.join(git_base_dir, '.gitignore')
            if os.path.exists(gitignore_path):
                self.assertTrue(self.does_gitignore_include_database(gitignore_path),
                                f"{FAILURE_HEADER}Your .gitignore does not include db.sqlite3.{FAILURE_FOOTER}")
            else:
                warnings.warn("No .gitignore found.")


class Chapter5ModelTests(TestCase):
    def setUp(self):
        category_py = Category.objects.get_or_create(name='Python', views=123, likes=55)
        Category.objects.get_or_create(name='Django', views=187, likes=90)
        Page.objects.get_or_create(category=category_py[0],
                                   title='Tango with Django',
                                   url='https://www.tangowithdjango.com',
                                   views=156)

    def test_category_model(self):
        category_py = Category.objects.get(name='Python')
        self.assertEqual(category_py.views, 123)
        self.assertEqual(category_py.likes, 55)

        category_dj = Category.objects.get(name='Django')
        self.assertEqual(category_dj.views, 187)
        self.assertEqual(category_dj.likes, 90)

    def test_page_model(self):
        category_py = Category.objects.get(name='Python')
        page = Page.objects.get(title='Tango with Django')
        self.assertEqual(page.url, 'https://www.tangowithdjango.com')
        self.assertEqual(page.views, 156)
        self.assertEqual(page.title, 'Tango with Django')
        self.assertEqual(page.category, category_py)

    def test_str_method(self):
        category_py = Category.objects.get(name='Python')
        page = Page.objects.get(title='Tango with Django')
        self.assertEqual(str(category_py), 'Python')
        self.assertEqual(str(page), 'Tango with Django')


class Chapter5AdminInterfaceTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('testAdmin', 'email@email.com', 'adminPassword123')
        self.client.login(username='testAdmin', password='adminPassword123')

        category = Category.objects.get_or_create(name='TestCategory')[0]
        Page.objects.get_or_create(title='TestPage1', url='https://www.google.com', category=category)

    def test_admin_interface_accessible(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200,
                         f"{FAILURE_HEADER}The admin interface is not accessible.{FAILURE_FOOTER}")

    def test_models_present(self):
        response = self.client.get('/admin/')
        body = response.content.decode()

        self.assertTrue('Models in the Rango application' in body,
                        f"{FAILURE_HEADER}Rango app not listed in admin.{FAILURE_FOOTER}")
        self.assertTrue('Categories' in body,
                        f"{FAILURE_HEADER}Category model missing in admin.{FAILURE_FOOTER}")
        self.assertTrue('Pages' in body,
                        f"{FAILURE_HEADER}Page model missing in admin.{FAILURE_FOOTER}")

    def test_page_display_changes(self):
        response = self.client.get('/admin/rango/page/')
        body = response.content.decode()

        # Django 2.2 sortable header checks
        self.assertTrue('<a href="?o=1">Title</a>' in body,
                        f"{FAILURE_HEADER}The 'Title' column is missing or in the wrong order.{FAILURE_FOOTER}")
        self.assertTrue('<a href="?o=2">Category</a>' in body,
                        f"{FAILURE_HEADER}The 'Category' column is missing or in the wrong order.{FAILURE_FOOTER}")
        self.assertTrue('<a href="?o=3">Url</a>' in body,
                        f"{FAILURE_HEADER}The 'Url' column is missing or in the wrong order.{FAILURE_FOOTER}")

        # Row content checks (Django 2.2 compatible)
        self.assertTrue('TestPage1' in body,
                        f"{FAILURE_HEADER}TestPage1 not found in admin list view.{FAILURE_FOOTER}")
        self.assertTrue('TestCategory' in body,
                        f"{FAILURE_HEADER}TestCategory not found in admin list view.{FAILURE_FOOTER}")
        self.assertTrue('https://www.google.com' in body,
                        f"{FAILURE_HEADER}URL for TestPage1 missing in admin list view.{FAILURE_FOOTER}")


class Chapter5PopulationScriptTests(TestCase):
    def setUp(self):
        try:
            import populate_rango
        except ImportError:
            raise ImportError(f"{FAILURE_HEADER}Cannot import populate_rango.{FAILURE_FOOTER}")

        if 'populate' not in dir(populate_rango):
            raise NameError(f"{FAILURE_HEADER}populate() missing in populate_rango.{FAILURE_FOOTER}")

        populate_rango.populate()

    def test_categories(self):
        categories = Category.objects.filter()
        self.assertEqual(len(categories), 3)

        names = list(map(str, categories))
        self.assertTrue('Python' in names)
        self.assertTrue('Django' in names)
        self.assertTrue('Other Frameworks' in names)

    def test_pages(self):
        details = {
            'Python': ['Official Python Tutorial', 'How to Think like a Computer Scientist', 'Learn Python in 10 Minutes'],
            'Django': ['Official Django Tutorial', 'Django Rocks', 'How to Tango with Django'],
            'Other Frameworks': ['Bottle', 'Flask']
        }

        for category in details:
            self.check_category_pages(category, details[category])

    def test_counts(self):
        details = {
            'Python': {'views': 128, 'likes': 64},
            'Django': {'views': 64, 'likes': 32},
            'Other Frameworks': {'views': 32, 'likes': 16}
        }

        for category in details:
            obj = Category.objects.get(name=category)
            self.assertEqual(obj.views, details[category]['views'])
            self.assertEqual(obj.likes, details[category]['likes'])

    def check_category_pages(self, category, titles):
        category_obj = Category.objects.get(name=category)
        pages = Page.objects.filter(category=category_obj)
        self.assertEqual(len(pages), len(titles))

        for title in titles:
            page = Page.objects.get(title=title)
            self.assertEqual(page.category, category_obj)
