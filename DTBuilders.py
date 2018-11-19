import json
from pprint import pprint

# create logger
import logging
import os
LEVEL = logging.INFO
logger = logging.getLogger(os.path.basename(__file__).split('.')[0] if __name__ == '__main__' else __name__)
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


class DT:
    def __init__(self):
        logger.debug('DT.__init__()')
        self.data = {}

    def get_dict(self):
        return self.data

    def get_json(self, compact=False):
        if compact:
            dt = json.dumps(self.data)
        else:
            dt =json.dumps(self.data, indent=4, separators=(',', ': '))
        #print('json', dt)
        return dt

    def with_ajax(self, data=None):
        if type(data) == type(' '):
            self.data['ajax'] = data
        elif type(data) == type({}):
            self.data['ajax'] = {}
            for d in data:
                self.data['ajax'][d] = data[d] if type(data[d]) == type(' ') else ''.join(data[d]) if type(data[d]) == type([]) else ''

        return self

class DTColumnBuilder(DT):
    def __init__(self):
        logger.debug('DTColumnBuilder.__init__()')
        DT.__init__(self)


    def new_column(self, data=''):
        self.data = {}
        if data or data is None:
            self.data['data'] = data
        return self



    def with_title(self, data=''):
        if data:
            self.data['title'] = data
        return self

    def with_default_content(self, data=''):
        if data:
            self.data['defaultContent'] = data
        return self


    def with_class(self, data=''):
        if data:
            self.data['className'] = data
        return self

    def with_edit_field(self, data=''):
        if data:
            self.data['editField'] = data
        return self



    def not_sortable(self):
        self.data['sortable'] = False
        return self


    def not_visible(self):
        self.data['visible'] = False
        return self



    def with_render(self, data=None):
        if type(data) == type(' ') and data:
            self.data['render'] = data
        elif type(data) == type([]):
            self.data['render'] = ''.join(data)
        return self

    def with_orderable(self, data):
        self.data['orderable'] = data
        return self

    def with_select_checkbox(self):
        self.data = {'data': None,
                        'defaultContent': '',
                        'className': 'select-checkbox',
                        'orderable': False
                      }
        return self


    def with_checkbox(self, data=None):
        if data:
            self.data['render'] = ''.join([
                "%%function ( data, type, row ) {",
                "if ( type === 'display' ) {",
                "  return '<input type=\"checkbox\" class=\"{Class}\">';".format(Class=data),
                "}",
                "  return data;",
                "},",
                "className:'dt-body-center'%%"
                ])
        return self


    def with_upload(self, image=False, details=False, length=False):
        if image:
            self.data['render'] = ''.join([
                "%%function ( file_id ) {",
                "  return  file_id ? '<img src=\"'+editor.file( 'files', file_id ).web_path+'\"/>' : null;"
                "}%%",
                ])
        elif details:
            self.data['render'] = ''.join([
                "%%function ( file_id ) {",
                "  return  file_id ? 'File: ' + editor.file( 'files', file_id ).filename +'<br>Uploaded: ' + editor.file( 'files', file_id ).timestamp +'<br>Size: ' + editor.file( 'files', file_id ).filesize : null;"
                "}%%",
                ])
        elif length:
            self.data['render'] = ''.join([
                "%%function ( d ) {",
                "  return  d ? d.length + ' files(s)' : 'No files';"
                "}%%",
                ])
        else:
            self.data['render'] = ''.join([
                "%%function ( file_id ) {",
                "  return  file_id ? 'File: ' + editor.file( 'files', file_id ).filename : null;"
                "}%%",
                ])
        return self


class DTOptionBuilder(DT):

    def __init__(self):
        logger.debug('DTOptionBuilder.__init__()')
        DT.__init__(self)


    def with_data(self, data=None):
        if data:
            self.data['data'] = data
        return self

    def with_dom(self, data=''):
        if data:
            self.data['dom'] = data
        return self


    def with_order(self, data):
        if data:
            self.data['order'] = data
        return self

    def with_row_id(self, data):
        if data:
            self.data['rowId'] = data
        return self

    def with_rowcallback(self, data=None):
        if type(data) == type(' ') and data:
            self.data['rowCallback'] = data
        elif type(data) == type([]):
            self.data['rowCallback'] = ''.join(data)
        return self

    def with_option(self, data=None):
        if type(data) == type({}):
            for d in data:
                self.data[d] = data[d]
        return self

    def not_paging(self):
        self.data['paging'] = False
        return self

    def not_ordering(self):
        self.data['ordering'] = False
        return self

class DTBuilder:

    def __init__(self):
        logger.debug('DTBuilder.__init__()')

    def get_js(self, options=None, columns=None, compact=False):
        #print ('get_js', type(options))
        js = ''
        dt_opts = []
        dt_cols = []
        if options:
            if type(options) == type(' '):
                try:
                    dt_opts = json.loads(options)
                except Exception as e:
                    print ('error load columns json', options)
                    print(e)
            elif type(options) == type({}):
                dt_opts = options
            #print('options result', options)
        for col in columns:
            if type(col) == type(' '):
                try:
                    dt_cols.append(json.loads(col))
                except Exception as e:
                    print ('error load columns json', col)
                    print(e)
            elif type(col) == type({}):
                dt_cols.append(col)

        if dt_cols:
            dt_opts['columns'] = dt_cols
        if compact:
            dt = json.dumps(dt_opts)
        else:
            dt = json.dumps(dt_opts, indent=4, separators=(',', ': '))

        dt = dt.replace('%%"', '')
        dt = dt.replace('"%%', '')

        return dt




class DTEFieldBuilder(DT):
    def __init__(self):
        logger.debug('DTEFieldBuilder.__init__()')
        DT.__init__(self)


    def new_field(self, data=''):
        self.data = {}
        if data:
            self.data['name'] = data
        return self

    def with_label(self, data=''):
        if data:
            self.data['label'] = data
        return self

    def with_type(self, data=''):
        if data:
            self.data['type'] = data
        return self

    def with_upload_display(self, image=False, details=False):
        if image:
            self.data['display'] = ''.join([
                "%%function ( file_id ) {",
                "  return  '<img src=\"'+editor.file( 'files', file_id ).web_path+'\"/>';"
                "}%%",
                ])
        elif details:
            self.data['display'] = ''.join([
                "%%function ( file_id ) {",
                "  return  'File: ' + editor.file( 'files', file_id ).filename +'<br>Uploaded: ' + editor.file( 'files', file_id ).timestamp +'<br>Size: ' + editor.file( 'files', file_id ).filesize;"
                "}%%",
                ])
        else:
            self.data['display'] = ''.join([
                "%%function ( file_id ) {",
                "  return  'File: ' + editor.file( 'files', file_id ).filename;"
                "}%%",
                ])

        return self

    def with_clear_text(self, data=''):
        if data:
            self.data['clearText'] = data
        return self

    def with_no_image_text(self, data=''):
        if data:
            self.data['noImageText'] = data
        return self

    def with_placeholder(self, data=''):
        if data:
            self.data['placeholder'] = data
        return self

    def with_checkbox(self):

        self.data['type'] = 'checkbox'
        self.data['separator'] = '|'
        self.data['unselectedValue'] = 0,
        self.data['options'] = [
            {'label': '', 'value': 1}
        ]
        return self

    def with_BT_checkbox(self):

        self.data['type'] = 'toggle'
        self.data['separator'] = '|'
        self.data['unselectedValue'] = 0,
        self.data['options'] = [
            {'label': '', 'value': 1}
        ]
        return self

    def with_option(self, data=None):
        if type(data) == type({}):
            for d in data:
                self.data[d] = data[d]
        return self

    def with_select2_options(self, data=None):
        if data:
            self.data['opts'] = data
        return self



class DTEOptionBuilder(DT):

    def __init__(self):
        logger.debug('DTEOptionBuilder.__init__()')
        DT.__init__(self)


    def with_table(self, data=None):
        if data:
            self.data['table'] = data
        return self


    def with_id_src(self, data=''):
        if data:
            self.data['idSrc'] = data
        return self

    def with_option(self, data=None):
        if type(data) == type({}):
            for d in data:
                self.data[d] = data[d]
        return self


class DTEBuilder:

    def __init__(self):
        logger.debug('DTBuilder.__init__()')

    def get_js(self, options=None, fields=None, compact=False):
        #print ('get_js', type(options))
        js = ''
        dt_opts = []
        dt_cols = []
        if options:
            if type(options) == type(' '):
                try:
                    dt_opts = json.loads(options)
                except Exception as e:
                    print ('error load columns json', options)
                    print(e)
            elif type(options) == type({}):
                dt_opts = options
            #print('options result', options)
        for col in fields:
            if type(col) == type(' '):
                try:
                    dt_cols.append(json.loads(col))
                except Exception as e:
                    print ('error load fields json', col)
                    print(e)
            elif type(col) == type({}):
                dt_cols.append(col)

        if dt_cols:
            dt_opts['fields'] = dt_cols
        if compact:
            dt = json.dumps(dt_opts)
        else:
            dt = json.dumps(dt_opts, indent=4, separators=(',', ': '))

        dt = dt.replace('%%"', '')
        dt = dt.replace('"%%', '')

        return dt


class DTSqlBuilder(DT):
    def __init__(self):
        logger.debug('DTSqlBuilder.__init__()')
        DT.__init__(self)
        self.dt_table = ''

    def new_select(self, data=None):
        self.data = {}
        self.data['table_order'] = []
        return self

    def create_new_table(self, data=None):
        if data and type(data) == type(' '):
            self.dt_table = data
            self.data[self.dt_table] = {}
            self.data['table_order'].append(self.dt_table)
        return self

    def with_table(self, data=None):
        if data:
            self.data[self.dt_table]['table'] = data
        return self

    def with_fields(self, data=None):
        if type(data) == type(' '):
            self.data[self.dt_table]['fields'] = [data]
        elif type(data) == type([]):
            self.data[self.dt_table]['fields'] = data
        return self

    def with_match(self, data=None):
        if data:
            self.data[self.dt_table]['match'] = data
        return self


    def with_select(self, fields=None, dt_object=None, multi_select=False, join_type='inner join', concat='', tags=False):
        if type(fields) == type(' '):
            self.data[self.dt_table]['fields'] = {'fields': [fields],
                                                  'pkid': 'pkid'} if multi_select else [fields]
        if type(fields) == type([]):
            self.data[self.dt_table]['fields'] = {'fields': fields,
                                                  'pkid': 'pkid'} if multi_select else fields
        elif type(fields) == type({}):
            pkid = fields.pop('pkid', 'pkid')
            if 'fields' in fields:
                self.data[self.dt_table]['fields'] = {'fields': [fields['fields']],
                                                      'pkid': pkid}
        if 'fields' in self.data[self.dt_table] and dt_object:
            self.data[self.dt_table]['select'] = 'multi' if multi_select else 'single'
            self.data[self.dt_table]['type'] = join_type
            self.data[self.dt_table]['tags'] = tags
            self.data[self.dt_table]['match'] = 'fk_{}{}'.format(self.data[self.dt_table]['table'],
                                                                 '_list' if multi_select else '')
            self.data[self.dt_table]['concat'] = concat
            self.data[self.dt_table]['dt_object'] = dt_object
        return self


if __name__ == '__main__':

    col = DTColumnBuilder()\
        .new_column('test')\
        .with_title('Test')\
        .not_sortable()\
        .not_visible()\
        .with_render(['function(data, type, full) {',
                   'return "<a>" + data + "</a>";',
                   '},'])\
        .get_json()

    #print(col)

    col = DTColumnBuilder()\
            .with_select_checkbox()\
            .get_json()
    #print(col)



    opt = DTOptionBuilder()\
            .with_ajax('data')\
            .with_option(data={'select': {'style': 'os', 'selector': 'td:first-child'}})\
            .get_json()
    #print(opt)

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
            .new_column('main.description')
            .with_title('Description')
            .with_render([
                "%%function ( data, type, row ) {",
                "if ( type === 'display' ) {",
                "  return '<input type=\"checkbox\" class=\"editor-enabled\">';",
                "}",
                "  return data;",
                "},",
                "className:'dt-body-center'%%",
            ]).get_json(),
    ]
    #print('[\n{}\n]'.format(',\n'.join(columns)))

    dt = DTBuilder().get_js(options=opt, columns=columns)

    #print (dt)

    dte_options = DTEOptionBuilder()\
                        .with_table('#main-table')\
                        .with_ajax('dt_test_page')\
                        .get_json()
    #print(dte_options)
    #print()
    #print()

    sql = DTSqlBuilder()\
            .new_select()\
            .create_new_table('main')\
            .with_table('test_page')\
            .with_fields(['pkid', 'name', 'description', 'enabled', 'toggle',
                            'fk_test_page_types', 'fk_test_page_lists_list']) \
            \
            .create_new_table('test_page_types') \
            .with_table('test_page_types') \
            .with_select(fields='name', dt_object='type_list') \
            \
            .create_new_table('test_page_lists')\
            .with_table('test_page_lists')\
            .with_select(fields=['name', 'description'], dt_object='test_list', multi_select=True, concat=': ')\
            .get_dict()

    pprint (sql)

