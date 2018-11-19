import os, sys
import datetime
import json
from collections import defaultdict
import re
from math import log, log10
import io


"""
testbed.py

Testbed websever using cherrypy
"""


"""
https://stackoverflow.com/questions/1210458/how-can-i-generate-a-unique-id-in-python
"""
import threading
_uid = threading.local()
def gen_uid():
    if getattr(_uid, "uid", None) is None:
        _uid.tid = threading.current_thread().ident
        _uid.uid = 0
    _uid.uid += 1
    return (_uid.tid, _uid.uid)

# create logger
import logging
import os
LEVEL = logging.INFO
logger = logging.getLogger(os.path.basename(__file__).split('.')[0] if __name__ == '__main__' else __name__.split('.')[1])
logger.setLevel(LEVEL)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(LEVEL)

# create formatter
formatter = logging.Formatter('%(asctime)s.%(msecs)03d: %(levelname)s: %(name)s.%(funcName)s(): %(message)s', datefmt='%m-%d-%Y %H:%M:%S')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)
# end create logger

import cherrypy
from cherrypy.lib import file_generator

from Database import Sqlite
from Datatables import Datatables
from Graph import Graph

from DTBuilders import DTOptionBuilder, DTColumnBuilder, DTBuilder, \
    DTEOptionBuilder, DTEFieldBuilder, DTEBuilder, DTSqlBuilder



def escape_sql(data):
    """
    Escape the " that might be in a string before creating sql string
    :param data: dictionary or string to escape "
    :return: updated data
    """

    if type(data) == type({}):
        for k, v in data.items():
            if '"' in v:
                data[k] = v.replace('"', r'\"')
    elif type(data) == type(' '):
        data = data.replace('"', r'\"')

    return data

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%m-%d-%Y %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class Testbed:

    def __init__(self):

        self.db = Sqlite(db = 'graphs.sqlite')
        self.dt = Datatables(db = 'graphs.sqlite')
        self.graphs = {}




    # todo: updated to be more accrute and added three_digit and bytes parameters
    # todo: changes made 7/9/2018, verify the changes work in production
    def human_readable_bytes(self, x, three_digit=False, bytes=True):
        """
        Convert large number into format small text with K, M, G, etc suffixes for display output
        :param x: large number to format
        :param three_digit: If True display 300GB instead of 0.30TB
        :param bytes: If True use 1024 bytes in expression else use 1000
        :return: formatted number for output
        """
        # hybrid of http://stackoverflow.com/a/10171475/2595465
        #      with http://stackoverflow.com/a/5414105/2595465
        if type(x) != type(1):
            if (type(x) == type(' ') or type(x) == type(' '.decode())) and x.isdigit():
                x = int(x)  #get int value of string x
            else:
                return x    #otherwise, unknown format, just return what was sent
        if x == 0:
            return '0'
        if bytes:
            magnitude = int(log(abs(x), 10.24))
            base = 1024
        else:
            magnitude = int(log10(abs(x)))
            base = 1000
        #print('magnitude, base', magnitude, base)
        if magnitude > 16:
            #print('Magnitude > 16')
            format_str = '%iP'
            denominator_mag = 15
            denominator = (base) ** (denominator_mag // 3)
        elif not three_digit:
            float_fmt = '%2.1f' if magnitude % 3 == 1 else '%1.2f'
            #print('float format', float_fmt)
            illion = (magnitude + 1) // 3
            #print('illion', illion)
            format_str = float_fmt + ['', 'K', 'M', 'G', 'T', 'P'][illion]
            denominator = (base) ** illion
        else:
            float_fmt = '%3.1f' if magnitude % 3 == 2 else '%2.1f' if magnitude % 3 == 1 else '%1.2f'
            #print('float format', float_fmt)
            illion = (magnitude) // 3
            #print('illion', illion)
            format_str = float_fmt + ['', 'K', 'M', 'G', 'T', 'P'][illion]
            denominator = (base) ** illion
        return (format_str % (x * 1.0 / (denominator)))

    def get_includes(self, libraries=None):
        css_includes = ''
        script_includes = ''

        if libraries is None:
            libraries = {'styling': 'DataTables',
                         'packages': ['DataTables', 'jQuery'],
                         'extensions': [],
                         'plugins': [],
                         }

        #validate libraries:
        styling = libraries.get('styling', '')
        if type(styling) != type(' ') or styling not in ['DataTables', 'Bootstrap 3', 'Bootstrap 4',
                                                         'jQuery UI', 'Foundation', 'Semantic UI']:
            styling = 'DataTables'     #default to DT styling if error
        libraries['styling'] = styling

        packages = libraries.get('packages', [])
        #print('original packages', packages)
        get_styling_package = False
        package_order = []
        if type(packages) != type([]) or len(packages) == 0:
            packages = ['DataTables']   #default to DT package if none listed or wrong format
        if 'jQuery' in packages:        #get jQuery first if defined
            package_order = package_order + ['jQuery']
            packages.remove('jQuery')

        if 'JSZip' in libraries['extensions']:        #if JSZip in extensions move to packages between jQuery and DT
            libraries['extensions'].remove('JSZip')
            package_order = package_order + ['JSZip']

        if styling in packages:         #next get styling package if defined, ie, Bootstrap 3 or DataTables
            package_order = package_order + [styling]
            packages.remove(styling)
            get_styling_package = True
        if styling !='DataTables' and 'DataTables' in packages:    #next get DataTables if defined and not the styling package
            package_order = package_order + ['DataTables']
            packages.remove('DataTables')

        libraries['packages'] = package_order
        #print('packages', libraries['packages'])

        if type(libraries['extensions']) == type(' '):
            libraries['extensions'] = [libraries['extensions']]  #if string only then put into list
        if type(libraries['extensions']) != type([]):       #if not list then default to blank list
            libraries['extensions'] = []


        #todo: validate buttons are defined if sub=extensions (HTML5 export, etc) are defined

        cdn_build = ''
        if libraries['styling'] == 'DataTables' or not get_styling_package:
            cdn_build += '/{}'.format(self.dt.get_styling_short_names(dt=libraries['styling']))
        else:
            cdn_build += '/{}-{}'.format(self.dt.get_styling_short_names(dt=libraries['styling']),
                                      self.dt.get_dt_versions(dt=libraries['styling']))
            libraries['packages'].remove(libraries['styling'])

        for c in libraries['packages']:
            cdn_build += '/{}-{}'.format(self.dt.get_dt_short_names(dt=c),
                                        self.dt.get_dt_versions(dt=c))

        #print('remaining packages', packages)
        #build additional external packages
        not_concat_cdn = [c for c in libraries['extensions'] if self.dt.get_dt_short_names(dt=c) == '']
        for c in not_concat_cdn:
            libraries['extensions'].remove(c)
        not_concat_cdn = not_concat_cdn + packages  #remaining package are not part of the CDN

        for c in libraries['extensions']:
            cdn_build += '/{}-{}'.format(self.dt.get_dt_short_names(dt=c),
                                        self.dt.get_dt_versions(dt=c))

        additional_includes = self.dt.get_external_includes(not_concat_cdn, styling)




        css_includes += '<!-- {} -->\n'.format(', '.join([libraries['styling']] + libraries['packages'] + libraries['extensions']))
        css_includes += '    <link rel="stylesheet" type="text/css" ' \
                        'href="https://cdn.datatables.net/v{cdn}/datatables.min.css"/>\n'.format(cdn=cdn_build)

        css_includes += additional_includes[0]  #add external includes

        css_includes += '    <!-- Font Awesome -->\n'
        css_includes += '    <link rel="stylesheet" ' \
                        'href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">\n'

        css_includes += '    <!-- Custom Theme Style -->\n'
        css_includes += '    <link rel="stylesheet" type="text/css" href="static/css/custom.min.css">\n'


        script_includes += '<!-- {} -->\n'.format(', '.join([libraries['styling']] + libraries['packages'] + libraries['extensions']))
        script_includes += '    <script type="text/javascript" ' \
                           'src="https://cdn.datatables.net/v{cdn}/datatables.min.js">' \
                           '</script>\n'.format(cdn=cdn_build)

        script_includes += additional_includes[1]  #add external includes

        script_includes += '    <!-- Custom Theme Scripts -->\n'
        script_includes += '    <script src="/static/js/custom.min.js"></script>\n'
        #script_includes += '    <!-- Bootstrap Toggle -->\n'
        #script_includes += '    <script src="static/js/bootstrap-toggle.min.js"></script>\n'
        #script_includes += '    <!-- Website Scripts -->\n'
        #script_includes += '    <script src="/static/js/website.js"></script>\n'

        plugins = libraries.get('plugins', [])

        for p in plugins:
            plugin_file = self.dt.get_plugins(p)
            if plugin_file:
                script_includes += '    <!-- {} -->\n'.format(p)
                script_includes += '    <script src="/static/js/{}"></script>\n'.format(plugin_file)

        return css_includes, script_includes



    def build_DT_page(self, page_name, libraries=None, css_styles='', child_name='',
                   datatables=None, editors=None, html_page=''):

        """

        :param page_name:
        :param libraries: Dictionary containing DT libraries based on Download bulder page and none DT libraries such as select2, quill
            {'styling': 'Bootstrap 3',   #string containing lib - DataTables, Bootstrap 3, Bootstrap 4, Foundation, jQuery UI, Semantic UI
                         'packages': [],  #list of packages - jQuery, DataTables, Editor, Select2, Quill, etc
                         'extensions': []  #list of DT extension like Buttons, Select
                         }
        :param css_styles:
        :param child_name: string or list containing child tables in order of display
        :param datatables:
        :param editors:
        :return:
        """
        if editors is None:
            editors = []

        if datatables is None:
            datatables = []

        if type(child_name) ==  type(' '):
            child_name = [child_name]

        child_name = [page_name] + child_name
        css_includes, script_includes = self.get_includes(libraries=libraries)


        with open('public/html/{}'.format(html_page if html_page else 'template.html')) as f:
            form = f.read()

        if html_page and '_template' not in html_page:
            form = form.replace('{script_includes}', script_includes)
            form = form.replace('{css_includes}', css_includes)
            #form = form.replace('Place instructions here', self.get_instructions(page_name))
        else:
            with open('public/html/table_template.html'.format(page_name)) as f:
                table_form = f.read()
            try:
                with open('public/html/{}_html.js'.format(page_name)) as f:
                    supplement_script = f.read()
            except:
                supplement_script = ''

            js_script = '$(document).ready(function() {\n'
            html_tables = ''

            editor_scripts = []
            global_variables = []
            for e in editors:
                #table_name = e.pop('table_name', '')
                variable = e.pop('variable', '')
                editor = DTEBuilder().get_js(options=e['options'], fields=e['fields'])

                if variable:
                    global_variables.append('var {};\n'.format(variable))

                edit = '\n{variable} = new $.fn.dataTable.Editor(\n'.format(variable=variable)
                edit += editor
                edit += ');\n\n'

                editor_scripts.append(edit)

            for d in datatables:
                table_title = d.pop('table_title', '')
                table_name = d.pop('table_name', '')
                variable = d.pop('variable', '')
                #dt = json.dumps(d, indent=4, separators=(',', ': '))
                dt = DTBuilder().get_js(options=d['options'], columns=d['columns'])
                if editor_scripts:
                    edit = editor_scripts.pop(0)
                else:
                    edit = ''
                js_script += edit
                js_script += '\nvar {variable} = $("#{table_name}").DataTable(\n'.format(variable=variable, table_name=table_name)
                js_script += dt
                js_script += ');\n\n'


                html_tables += table_form.format(table_title=table_title, table_name=table_name)

                #html_tables = html_tables.replace('Place instructions here', self.get_instructions(child_name.pop(0)))


            js_script += supplement_script
            js_script += '});\n'

            js_script = '{}\n{}'.format(';\n'.join(global_variables), js_script)

            form = form.format(css_includes=css_includes,
                               script_includes=script_includes,
                               page_name=page_name,
                               css_styles=css_styles,
                               js_script=js_script,
                               html_tables=html_tables,
                               )

            #for child in child_name:   #if any children left try to place the instructions in the form
            #    form = form.replace('Place {} instructions here'.format(child), self.get_instructions(child))


        #form = form.replace('<!-- sidebar menu -->', self.get_instructions('sidebar'))

        return form


    ######################
    #
    # Index
    #
    ######################
    @cherrypy.expose
    def index(self, *args, **kwargs):
        with open('public/html/index.html') as f:
            form = f.read()
        #form = form.replace('<!-- sidebar menu -->', self.get_instructions('sidebar'))
        return form




    ######################
    #
    # Upload files
    #
    ######################
    @cherrypy.expose
    def graph_upload(self, **kwargs):
        page_name = sys._getframe().f_code.co_name
        datatables = []
        editors = []

        libraries = {'styling': 'Bootstrap 3',
                     'packages': ['Bootstrap 3', 'DataTables', 'jQuery', 'Editor'],
                     'extensions': ['Natural', 'Bootstrap Toggle', 'Select', 'Buttons',
                                    'HTML5 export', 'JSZip'],
                     'plugins': [],
                     }
        columns = [
            DTColumnBuilder()
                .new_column('main.pkid')
                .with_title('pkid')
                .not_sortable()
                .not_visible()
                .get_json(),
            DTColumnBuilder()
                .with_select_checkbox()
                .with_title('')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.name')
                .with_title('Name')
                .get_json(),
            DTColumnBuilder()
                .new_column('files')
                .with_title('Multiple Files')
                .with_edit_field('files[].id')
                .with_default_content('No image')
                .with_upload(length=True)
                .get_json(),
        ]

        datatables.append({
            'table_name': 'main-table',  # define html ID for table
            'table_title': 'Graph File Upload',  # Table HTML title
            'variable': 'table',  # JS variable to assign table
            'columns': columns,
            'options': DTOptionBuilder()
                            .with_ajax('dt_graph_upload')
                            .with_option(data={'select': {'style': 'os', 'selector': 'td:first-child'}})
                            .get_json()


        }
        )

        fields = [
            DTEFieldBuilder()
                .new_field('main.pkid')
                .with_label('pkid:')
                .with_type('hidden')
                .get_dict(),
            DTEFieldBuilder()
                .new_field('main.name')
                .with_label('Name:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('files[].id')
                .with_label('Multiple Files:')
                .with_type('uploadMany')
                .with_upload_display()
                .with_clear_text('Clear')
                .with_no_image_text('No image')
                .get_json(),

        ]

        editors.append({
                    'variable': 'editor',                #JS variable to assign table
                    'options': DTEOptionBuilder()
                        .with_table('#main-table')     #define html ID for table
                        .with_ajax('dt_graph_upload')             #start of DT init code
                        .get_dict(),
                    'fields': fields

                    })
        form = self.build_DT_page(page_name, datatables=datatables,
                               editors=editors, libraries=libraries)
        return form

    @cherrypy.expose
    def dt_graph_upload(self, *args, **kwargs):

        fields = DTSqlBuilder()\
                    .new_select()\
                    .create_new_table('main')\
                    .with_table('graph_files')\
                    .with_fields(['pkid', 'name', 'uploaded_files']) \
                    .get_dict()
        #print(kwargs)
        if kwargs.get('action', '') == 'upload':
            kwargs['request_body'] = cherrypy.request.body

        result = self.dt.parse_request(fields=fields, debug=True, get_uploads=True, uploadMany={'files': 'uploaded_files'}, *args, **kwargs)


        #print(result)
        return json.dumps(result, cls=DatetimeEncoder)


    ######################
    #
    # TextFSM Scripts
    #
    ######################
    @cherrypy.expose
    def textfsm(self, **kwargs):
        page_name = sys._getframe().f_code.co_name
        datatables = []
        editors = []

        libraries = {'styling': 'Bootstrap 3',
                     'packages': ['Bootstrap 3', 'DataTables', 'jQuery', 'Editor'],
                     'extensions': ['Natural', 'Bootstrap Toggle', 'Select', 'Buttons',
                                    'HTML5 export', 'JSZip', 'Quill'],
                     'plugins': [],
                     }
        columns = [
            DTColumnBuilder()
                .new_column('main.pkid')
                .with_title('pkid')
                .not_sortable()
                .not_visible()
                .get_json(),
            DTColumnBuilder()
                .with_select_checkbox()
                .with_title('')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.name')
                .with_title('Name')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.script')
                .with_title('Script')
                .get_json(),
        ]

        datatables.append({
            'table_name': 'main-table',  # define html ID for table
            'table_title': 'TextFSM Script Tool',  # Table HTML title
            'variable': 'table',  # JS variable to assign table
            'columns': columns,
            'options': DTOptionBuilder()
                            .with_ajax('dt_textfsm')
                            .with_option(data={'select': {'style': 'os', 'selector': 'td:first-child'}})
                            .get_json()


        }
        )

        fields = [
            DTEFieldBuilder()
                .new_field('main.pkid')
                .with_label('pkid:')
                .with_type('hidden')
                .get_dict(),
            DTEFieldBuilder()
                .new_field('main.name')
                .with_label('Name:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.script')
                .with_label('Script:')
                .with_type('quill_text')
                .get_json(),

        ]

        editors.append({
                    'variable': 'editor',                #JS variable to assign table
                    'options': DTEOptionBuilder()
                        .with_table('#main-table')     #define html ID for table
                        .with_ajax('dt_textfsm')             #start of DT init code
                        .get_dict(),
                    'fields': fields

                    })
        form = self.build_DT_page(page_name, datatables=datatables,
                               editors=editors, libraries=libraries)
        return form

    @cherrypy.expose
    def dt_textfsm(self, *args, **kwargs):

        fields = DTSqlBuilder()\
                    .new_select()\
                    .create_new_table('main')\
                    .with_table('textfsm')\
                    .with_fields(['pkid', 'name', 'script']) \
                    .get_dict()
        print(kwargs)

        if 'action' in kwargs:
            for r in kwargs:
                print(r)
                if '[script]' in r:
                    kwargs[r] = re.sub(r'\\', r'\\\\', kwargs[r])
                    print('replacing', kwargs[r])
                    print('replacing', repr(kwargs[r]))

        #print(kwargs)
        result = self.dt.parse_request(fields=fields, debug=True, *args, **kwargs)

        #print(result)
        #print(result)
        return json.dumps(result, cls=DatetimeEncoder)


    ######################
    #
    # Perfmon Templates
    #
    ######################
    @cherrypy.expose
    def perfmon(self, **kwargs):
        page_name = sys._getframe().f_code.co_name
        datatables = []
        editors = []

        libraries = {'styling': 'Bootstrap 3',
                     'packages': ['Bootstrap 3', 'DataTables', 'jQuery', 'Editor', 'Select2'],
                     'extensions': ['Buttons', 'Select'],
                     'plugins': [],
                     }
        columns = [
            DTColumnBuilder()
                .new_column('main.pkid')
                .with_title('pkid')
                .not_sortable()
                .not_visible()
                .get_json(),
            DTColumnBuilder()
                .with_select_checkbox()
                .with_title('')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.name')
                .with_title('Name')
                .get_json(),
            DTColumnBuilder()
                .new_column('perfmon_list.name')
                .with_title('Perfmon Counter')
                .with_edit_field('main.fk_perfmon_counters')
                .get_json(),
        ]

        datatables.append({
            'table_name': 'main-table',  # define html ID for table
            'table_title': 'Perfmon Template Tool',  # Table HTML title
            'variable': 'table',  # JS variable to assign table
            'columns': columns,
            'options': DTOptionBuilder()
                            .with_ajax('dt_perfmon')
                            .with_option(data={'select': {'style': 'os', 'selector': 'td:first-child'}})
                            .get_json()


        }
        )

        fields = [
            DTEFieldBuilder()
                .new_field('main.pkid')
                .with_label('pkid:')
                .with_type('hidden')
                .get_dict(),
            DTEFieldBuilder()
                .new_field('main.name')
                .with_label('Name:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.fk_perfmon_counters')
                .with_label('Perfmon Counter:')
                .with_type('select2')
                .with_select2_options({'tags': True,
                                       'allowClear': True,
                                        'placeholder': 'Select Device Types'})
                .get_json(),

        ]

        editors.append({
                    'variable': 'editor',                #JS variable to assign table
                    'options': DTEOptionBuilder()
                        .with_table('#main-table')     #define html ID for table
                        .with_ajax('dt_perfmon')             #start of DT init code
                        .get_dict(),
                    'fields': fields

                    })
        form = self.build_DT_page(page_name, datatables=datatables,
                               editors=editors, libraries=libraries)
        return form

    @cherrypy.expose
    def dt_perfmon(self, *args, **kwargs):

        fields = DTSqlBuilder()\
                    .new_select()\
                    .create_new_table('main')\
                    .with_table('perfmon_templates')\
                    .with_fields(['pkid', 'name', 'fk_perfmon_counters', 'options']) \
                    \
                    .create_new_table('perfmon_counters') \
                    .with_table('perfmon_counters') \
                    .with_select(fields='name', dt_object='perfmon_list', tags=True, join_type='left join') \
                    .get_dict()
        print(kwargs)

        if 'action' in kwargs:
            pass

        #print(kwargs)
        result = self.dt.parse_request(fields=fields, debug=True, *args, **kwargs)

        #print(result)
        #print(result)
        return json.dumps(result, cls=DatetimeEncoder)


    ######################
    #
    # Graph
    #
    ######################
    @cherrypy.expose
    def graph(self, **kwargs):
        page_name = sys._getframe().f_code.co_name
        datatables = []
        editors = []

        libraries = {'styling': 'Bootstrap 3',
                     'packages': ['Bootstrap 3', 'DataTables', 'jQuery', 'Editor', 'Select2'],
                     'extensions': ['Natural', 'Bootstrap Toggle', 'Select', 'Buttons',
                                    'HTML5 export', 'JSZip'],
                     'plugins': [],
                     }
        columns = [
            DTColumnBuilder()
                .new_column('main.pkid')
                .with_title('pkid')
                .not_sortable()
                .not_visible()
                .get_json(),
            DTColumnBuilder()
                .with_select_checkbox()
                .with_title('')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.name')
                .with_title('Name')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.description')
                .with_title('Description')
                .get_json(),
            DTColumnBuilder()
                .new_column('source.name')
                .with_title('Graph Source')
                .with_edit_field('main.fk_graph_sources')
                .get_json(),
            DTColumnBuilder()
                .new_column('textfsm.name')
                .with_title('TextFSM Script')
                .with_class('graph-filter')
                .with_edit_field('main.fk_textfsm')
                .get_json(),
            DTColumnBuilder()
                .new_column('perfmon_counter.name')
                .with_title('Perfmon Counter')
                .with_edit_field('main.fk_perfmon_counters')
                .get_json(),
            DTColumnBuilder()
                .new_column('graphs.name')
                .with_title('Graph Files')
                .with_edit_field('main.fk_graph_files')
                .get_json(),
        ]

        datatables.append({
            'table_name': 'main-table',  # define html ID for table
            'table_title': 'Graphing Tool',  # Table HTML title
            'variable': 'table',  # JS variable to assign table
            'columns': columns,
            'options': DTOptionBuilder()
                            .with_ajax('dt_graph')
                            .with_option(data={'select': {'style': 'single', 'selector': 'td:first-child'}})
                            .get_json()


        }
        )

        fields = [
            DTEFieldBuilder()
                .new_field('main.pkid')
                .with_label('pkid:')
                .with_type('hidden')
                .get_dict(),
            DTEFieldBuilder()
                .new_field('main.name')
                .with_label('Name:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.graph_options')
                .with_label('Description:')
                .with_type('hidden')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.description')
                .with_label('Description:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.fk_graph_sources')
                .with_label('Graph Source:')
                .with_type('select2')
                .with_select2_options({'allowClear': True,
                                        'placeholder': 'Select Type of Graph'})
                .get_json(),

            DTEFieldBuilder()
                .new_field('main.fk_textfsm')
                .with_label('TextFSM Script:')
                .with_type('select2')
                .with_select2_options({'allowClear': True,
                                        'placeholder': 'Select TextFSM Script'})
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.fk_perfmon_counters')
                .with_label('Perfmon Counter:')
                .with_type('select2')
                .with_select2_options({'tags': True,
                                       'allowClear': True,
                                        'placeholder': 'Select or Enter counter'})
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.fk_graph_files')
                .with_label('Graph Files:')
                .with_type('select2')
                .with_select2_options({'allowClear': True,
                                        'placeholder': 'Select Files'})
                .get_json(),
        ]

        editors.append({
                    'variable': 'editor',                #JS variable to assign table
                    'options': DTEOptionBuilder()
                        .with_table('#main-table')     #define html ID for table
                        .with_ajax('dt_graph')             #start of DT init code
                        .get_dict(),
                    'fields': fields

                    })
        form = self.build_DT_page(page_name, datatables=datatables, child_name='graph_builder',
                               editors=editors, libraries=libraries, html_page='graph_template.html')
        return form

    @cherrypy.expose
    def dt_graph(self, *args, **kwargs):

        fields = DTSqlBuilder()\
                    .new_select()\
                    .create_new_table('main')\
                    .with_table('graph')\
                    .with_fields(['pkid', 'name', 'description', 'fk_graph_files', 'fk_perfmon_counters',
                                  'fk_graph_sources', 'fk_textfsm', 'graph_options']) \
                    \
                    .create_new_table('graph_sources') \
                    .with_table('graph_sources') \
                    .with_select(fields=['name', 'title', 'field'], dt_object='source', join_type='left join') \
                    \
                    .create_new_table('graph_files') \
                    .with_table('graph_files') \
                    .with_select(fields='name', dt_object='graphs', join_type='left join') \
                    \
                    .create_new_table('textfsm') \
                    .with_table('textfsm') \
                    .with_select(fields='name', dt_object='textfsm', join_type='left join') \
                    \
                    .create_new_table('perfmon_counters') \
                    .with_table('perfmon_counters') \
                    .with_select(fields='name', dt_object='perfmon_counter', tags=True, join_type='left join') \
                    .get_dict()
        #print(kwargs)
        if kwargs.get('action', '') == 'upload':
            kwargs['request_body'] = cherrypy.request.body

        result = self.dt.parse_request(fields=fields, debug=True, *args, **kwargs)


        #print(result)
        return json.dumps(result, cls=DatetimeEncoder)

    @cherrypy.expose
    def save_graph_options(self, **kwargs):

        #print(kwargs)

        graph_options = json.dumps(kwargs.get('graph_options', {}))

        pkid = kwargs.get('pkid', 0)

        if pkid:
            sql = 'update graph set graph_options = {} where pkid = "{}"'.format(graph_options, pkid)
            #print(sql)
            self.db.db_command(sql=sql)

        return None


    @cherrypy.expose
    def get_graph_info(self, **kwargs):

        #print(kwargs)
        fk_graph_files = kwargs.get('fk_graph_files', 0)
        fk_textfsm = kwargs.get('fk_textfsm', 0)
        fk_perfmon_counters = kwargs.get('fk_perfmon_counters', 0)
        fk_graph_sources = kwargs.get('fk_graph_sources', 0)
        graph_id = int(kwargs.get('graph_id', -1))

        files = []
        filter_data = ''
        filter_desc = ''
        source_field = ''

        #get file names and info (size, date uploaded)
        if fk_graph_files:

            sql = 'select uploaded_files from graph_files where pkid = "{}"'.format(fk_graph_files)
            uid = gen_uid()
            result = self.db.db_command(sql=sql, uid=uid).one(uid)

            if result:

                try:
                    result = json.loads(result['uploaded_files'])
                except:
                    result = []

                graph_files = [r['id'] for r in result]

                if graph_files:
                    sql = 'select filename, filesize, timestamp, web_path from uploads where pkid in ({})'.format(','.join(graph_files))

                    uid = gen_uid()
                    files = self.db.db_command(sql=sql, uid=uid).all(uid)


        #get graph source and Pandas Filter table small description
        if fk_graph_sources:
            sql = 'select description, field from graph_sources where pkid = "{}"'.format(fk_graph_sources)
            uid = gen_uid()
            result = self.db.db_command(sql=sql, uid=uid).one(uid)

            if result:
                source_field = result['field']
                filter_desc = result['description']

        #get filter
        if source_field:
            if source_field == 'fk_textfsm':
                sql = 'select script as filter from textfsm where pkid = "{}"'.format(fk_textfsm)
            elif source_field == 'fk_perfmon_counters':
                sql = 'select name as filter from perfmon_counters where pkid = "{}"'.format(fk_perfmon_counters)
            else:
                sql = ''
            if sql:
                uid = gen_uid()
                result = self.db.db_command(sql=sql, uid=uid).one(uid)

                if result:

                    filter_data = result['filter'].replace('\n', '<br>').replace(' ', '&nbsp;')



        #generate new graph process ID if new connection
        if graph_id == -1:
            graph_id = self.init_graph()

        return json.dumps({'files': files, 'filter_data': filter_data, 'filter_type': source_field, 'filter_desc': filter_desc, 'graph': graph_id}, cls=DatetimeEncoder)

    @cherrypy.expose
    def clear_graph(self, **kwargs):

        graph_id = kwargs.get('id', -1)
        kill_process = kwargs.get('kill', 'false')

        kill_process = True if kill_process == 'true' else False

        self.remove_graph(int(graph_id), kill_process)


    @cherrypy.expose
    def get_dataframe(self, **kwargs):

        print(kwargs)

        length = 0
        df_head = ''
        graph_id = int(kwargs.get('id', -1))
        files = kwargs.get('files[]', [])
        filter_type = kwargs.get('filter_type', '')
        filter_data = kwargs.get('filter_data', '')

        #if filter_type == 'fk_textfsm':
        filter_data = filter_data.replace('<br>', '\n').replace('&nbsp;', ' ')

        grapher = self.graphs[graph_id]  #graph object for process ID
        #print(template)
        if files:

            if filter_type == 'fk_textfsm':
                grapher.get_text_files(files)
                result = grapher.textfsm_parse(filter_data)
                grapher.get_dataframe(result, filter_type)
            elif filter_type == 'fk_perfmon_counters':
                grapher.get_csv_files(files)
                grapher.perfmon_parse(filter_data)
            else:
                return json.dumps({'error': 'Unable to determine Pandas DF filter type: filter_type = "{}"'.format(filter_type)})
            #print(result)

            #if result and 'error' in result:
            #    return json.dumps(result)


        #print(self.graphs[graph_id].df.head())

        df_head = str(grapher.df.head()).replace('\n', '<br>').replace(' ', '&nbsp;')
        df_tail = str(grapher.df.tail()).replace('\n', '<br>').replace(' ', '&nbsp;')
        length = len(grapher.df.index)
        hostnames = list(grapher.df.Hostname.unique())
        columns = list(grapher.df.columns.values)

        df2 = grapher.df.groupby('Timestamp').first()
        start_time = df2.first_valid_index()
        end_time = df2.last_valid_index()

        #print(type(columns),columns)
        #print(grapher.df.shape)

        return json.dumps({'df_head': '{}<br>....<br>{}'.format(df_head, df_tail),
                           'df_length': length,
                           'hostnames': hostnames,
                           'columns': columns,
                           'start_time': start_time,
                           'end_time': end_time,
                           })

    @cherrypy.expose
    def get_pd_graph(self, **kwargs):

        kwargs['legend'] = True if kwargs.get('legend', '') == 'true' else False
        kwargs['group_by'] = True if kwargs.get('group_by', '') == 'true' else False

        graph_id = int(kwargs.get('id', -1))

        if graph_id >= 0:
            result = self.graphs[graph_id].get_graph(**kwargs)
        else:
            result = {'error': 'Unable to determine the process ID for this web page.  please relaod and try again.'}

        #print(result)
        #cherrypy.response.headers['Content-Type'] = "image/png"

        if 'error' in result:
            return json.dumps(result)
        else:
            return '<img src="data:image/png;base64,{}" width="384" height="288" border="0"/>'.format(result['data'].decode('utf-8'))  #width="640" height="480" border="0"

    def init_graph(self):

        graph_keys = self.graphs.keys()

        if graph_keys:
            next_graph = max(graph_keys) + 1
        else:
            next_graph = 0

        self.graphs[next_graph] = Graph()

        return next_graph


    def remove_graph(self, graph_id, kill_process):

        if graph_id in self.graphs:
            self.graphs[graph_id].clear_dataframe()
            if kill_process:
                self.graphs.pop(graph_id, None)






    ######################
    #
    # Test2 - example page
    # Uses new DTBuilder API
    #
    ######################
    @cherrypy.expose
    def test_page2(self):
        page_name = sys._getframe().f_code.co_name

        datatables = []
        editors = []

        libraries = {'styling': 'Bootstrap 3',
                     'packages': ['Bootstrap 3', 'DataTables', 'jQuery', 'Editor', 'Select2'],
                     'extensions': ['Buttons', 'HTML5 export', 'Select', 'JSZip', 'PDFMake', 'Bootstrap Toggle'],
                     'plugins': ['fieldType.toggle'],
                     }


        columns = [
            DTColumnBuilder()
                .new_column('main.pkid')
                .with_title('pkid')
                .not_sortable()
                .not_visible()
                .get_json(),
            DTColumnBuilder()
                .with_select_checkbox()
                .with_title('')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.name')
                .with_title('Name')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.description')
                .with_title('Description')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.enabled')
                .with_title('Enabled')
                .with_checkbox('editor-enabled')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.toggle')
                .with_title('BT Toggle')
                .with_checkbox('editor-toggle')
                .get_json(),
            DTColumnBuilder()
                .new_column('type_list.name')
                .with_title('Type')
                .with_edit_field('main.fk_test_page_types')
                .get_json(),
            DTColumnBuilder()
                .new_column('test_list')
                .with_title('test List')
                .with_edit_field('main.fk_test_page_lists_list[]')
                .with_render('[, ].label')
                .get_json(),
            DTColumnBuilder()
                .new_column('main.single_file')
                .with_title('Single File')
                .with_default_content('No image')
                .with_upload(details=True)
                .get_json(),
            DTColumnBuilder()
                .new_column('files')
                .with_title('Multiple Files')
                .with_edit_field('files[].id')
                .with_default_content('No image')
                .with_upload(length=True)
                .get_json(),
        ]

        datatables.append({
            'table_name': 'main-table',  # define html ID for table
            'table_title': 'Main Test Table 2',  # Table HTML title
            'variable': 'table',  # JS variable to assign table
            'columns': columns,
            'options': DTOptionBuilder()
                            .with_ajax('dt_test_page2')
                            .with_option(data={'select': {'style': 'os', 'selector': 'td:first-child'}})
                            .with_option(data={'pageLength': 1})
                            .with_rowcallback([
                                "%%function ( row, data ) { ",
                               "$('input.editor-enabled', row).prop( 'checked', data.main.enabled == 1 );",
                               "$('input.editor-toggle ', row).prop( 'checked', data.main.toggle == 1 ).bootstrapToggle({size: 'mini'});",
                               "}%%"  # .bootstrapToggle({size: 'mini'});
                            ])
                            .get_json()


        }
        )


        fields = [
            DTEFieldBuilder()
                .new_field('main.pkid')
                .with_label('pkid:')
                .with_type('hidden')
                .get_dict(),
            DTEFieldBuilder()
                .new_field('main.name')
                .with_label('Name:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.description')
                .with_label('Description:')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.enabled')
                .with_label('Enabled:')
                .with_checkbox()
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.toggle')
                .with_label('BT Toggle:')
                .with_BT_checkbox()
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.fk_test_page_types')
                .with_label('Type Name:')
                .with_type('select')
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.fk_test_page_lists_list[]')
                .with_label('Page List:')
                .with_type('select2')
                .with_select2_options({'multiple': True,
                                        'placeholder': 'Select Device Types'})
                .get_json(),
            DTEFieldBuilder()
                .new_field('main.single_file')
                .with_label('Single File:')
                .with_type('upload')
                .with_upload_display(details=True)
                .with_clear_text('Clear')
                .with_no_image_text('No image')
                .get_json(),
            DTEFieldBuilder()
                .new_field('files[].id')
                .with_label('Multiple Files:')
                .with_type('uploadMany')
                .with_upload_display()
                .with_clear_text('Clear')
                .with_no_image_text('No image')
                .get_json(),
        ]

        editors.append({
                    'variable': 'editor',                #JS variable to assign table
                    'options': DTEOptionBuilder()
                        .with_table('#main-table')     #define html ID for table
                        .with_ajax('dt_test_page2')             #start of DT init code
                        .get_dict(),
                    'fields': fields

                    })

        form = self.build_DT_page(page_name, datatables=datatables,
                               editors=editors, libraries=libraries)
        return form

    @cherrypy.expose
    def dt_test_page2(self, *args, **kwargs):

        fields = DTSqlBuilder()\
                    .new_select()\
                    .create_new_table('main')\
                    .with_table('test_page')\
                    .with_fields(['pkid', 'name', 'description', 'enabled', 'toggle',
                                    'fk_test_page_types', 'fk_test_page_lists_list',
                                  'single_file', 'multi_file'
                                  ]) \
                    \
                    .create_new_table('test_page_types') \
                    .with_table('test_page_types') \
                    .with_select(fields='name', dt_object='type_list') \
                    \
                    .create_new_table('test_page_lists')\
                    .with_table('test_page_lists')\
                    .with_select(fields=['name', 'description'], dt_object='test_list', multi_select=True, concat=': ')\
                    \
                    .get_dict()
                    #.create_new_table('files')\
                    #.with_table('test_page')\
                    #.with_fields('multi_file')\


        #print(fields)
        #print(kwargs)

        if kwargs.get('action', '') == 'upload':
            kwargs['request_body'] = cherrypy.request.body


        result = self.dt.parse_request(fields=fields, debug=True, get_uploads=True, uploadMany={'files': 'multi_file'}, *args, **kwargs)
        return json.dumps(result, cls=DatetimeEncoder)




if __name__ == '__main__':
    conf = {
        '/': {
            'tools.sessions.on': True,
            # 'tools.caching.on': True,
            # 'tools.caching.force' : True,
            'tools.staticdir.root': os.path.abspath(os.getcwd())
        },
        '/static': {
            'tools.staticdir.on': True,
            # 'tools.caching.on': True,
            # 'tools.caching.force' : True,
            'tools.staticdir.dir': './public'
        }
    }

    webapp = Testbed()
    cherrypy.config.update(
        {'server.socket_host': '0.0.0.0',
         'server.socket_port': 3000,
         'log.screen': True,
         'log.error_file': '',
         'log.access_file': ''
         }
    )
    cherrypy.quickstart(webapp, '/', conf)
