import io
from datetime import datetime
from io import BytesIO
import base64
import re
from pathlib import Path
from math import log

## SET BACKEND for Matplotlib
from matplotlib import use as mpl_use
mpl_use('Agg')


from matplotlib.ticker import MultipleLocator, FixedFormatter, FormatStrFormatter, FuncFormatter

import textfsm

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

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


DEFAULT_INTERVAL = 15

PATH = './public/uploads/'


"""
Python is not installed as a framework. The Mac OS X backend will not be able to function correctly 
if Python is not installed as a framework. See the Python documentation for more information on 
installing Python as a framework on Mac OS X. Please either reinstall Python as a framework, 
or try one of the other backends. If you are using (Ana)Conda please install python.app and 
replace the use of 'python' with 'pythonw'. See 'Working with Matplotlib on OSX' 
in the Matplotlib FAQ for more information.
"""
def check_for_TkAgg():
    # Apply workaround (for above Framework issue) of adding `backend: TkAgg` to ~/.matplotlib/matplotlibrc
    # https://stackoverflow.com/questions/21784641/installation-issue-with-matplotlib-python

    home = Path.home()

    matplotlib = home / '.matplotlib'

    if matplotlib.is_dir():
        matplotlibrc = matplotlib / 'matplotlibrc'

        if matplotlibrc.is_file():
            # check for workaround
            workaround = False

            # open file and get text contents
            contents = ''

            if 'backend: TkAgg' in contents:
                workaround = True

            # add workaround if not in matplotlibrc
            if not workaround:
                add_TkAgg_workaround(matplotlibrc)
        else:
            # create matplotlibrc
            add_TkAgg_workaround(matplotlibrc)
            pass

    else:
        print('Unable to validate matplotlib install.  Did not find directory "{}"'.format(matplotlib))


def add_TkAgg_workaround(filename):
    # open file, create is it doesn't exists

    # append `backend: TkAgg\n` to file and close

    pass



# todo: update function to be more accurate
def human_readable_bytes(x, *args):
    """
    Convert large number string to readable number like 2.4G
    :param x: The large number to convert
    :param *args: Not used at this time
    :return:
    """
    # hybrid of http://stackoverflow.com/a/10171475/2595465
    #      with http://stackoverflow.com/a/5414105/2595465
    # changed (1024 ** illion) to (1000 ** illion)
    if 'numpy.float64' in str(type(x)):
        x = int(x)
    if type(x) != type(1):
        if (type(x) == type(' ') or type(x) == type(' '.decode())) and x.isdigit():
            x = int(x)
        else:
            return x
    if x == 0:
        return '0'
    magnitude = int(log(abs(x), 10.24))
    if magnitude > 16:
        format_str = '%iP'
        denominator_mag = 15
    else:
        float_fmt = '%2.1f' if magnitude % 3 == 1 else '%1.2f'
        illion = (magnitude + 1) // 3
        format_str = float_fmt + ['', 'K', 'M', 'G', 'T', 'P'][illion]
    #print x, (format_str % (x * 1.0 / (1000 ** illion)))  # .lstrip('0')
    return (format_str % (x * 1.0 / (1000 ** illion)))  # .lstrip('0')


def parse_datetime(date_time_str, include_msec=False):
    """
    Used for converting CSV file timestamp to Pandas time format
    :param date_time_str:
    :param include_msec:
    :return:
    """
    #print ('date_time_str', date_time_str)
    if include_msec:
        return datetime.strptime(date_time_str, '%m/%d/%Y %H:%M:%S.%f')
    else:
        date_time_str = date_time_str.split('.')[0]   #remove msec
        return pd.to_datetime(date_time_str)   #return Pandas date time format
        #return datetime.strptime(date_time_str, '%m/%d/%Y %H:%M:%S')


class Graph:

    def __init__(self):

        self.textfsm_object = None
        self.df = None
        self.data = ''
        self.fig = None
        self.ax = None

    def get_headings(self, headers, title=False):
        """
        Return list of headings replacing underscores with spaces
        :param headers: List of header strings
        :param titles: True will force first character of each word to upper case
        """
        headings = []

        for h in headers:
            headings.append(' '.join([w.title() if title and w.upper() != w else w for w in h.split('_')]))

        return headings

    def convert_ip_to_name(self, data):
        #print 'converting ip to name'
        cols = list(data.columns.values)
        updated_cols = []
        REGEX = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        for c in cols:
            match = re.search(REGEX, c)
            if match:
                hostname = get_hostname(match.group())
                temp = c.replace(match.group(), hostname)
                updated_cols.append(temp)
            else:
                updated_cols.append(c)
        return updated_cols


    def get_text_files(self, filenames):
        result = ''
        for filename in filenames:
            with open(filename) as f:
                result += f.read()
        self.data = result

    def get_csv_files(self, filenames):

        self.data = []
        #print(filenames)

        for filename in filenames:
            data = pd.read_csv(filename,
                                header=0,
                                #index_col=0,
                                #converters={0: parse_datetime},
                               #include_msec=False,
                                low_memory=False)   #remove warning message

            #print(type(data))
            #cols = list(data.columns.values)
            #print(cols)
            #data.columns = self.convert_ip_to_name(data)
            #data.columns = map(str.lower, data.columns)   # normalize colmn names to lower case
            #data = data.rename(columns={cols[0]: 'timestamp'})

            self.data.append(data)



    def textfsm_parse(self, template):

        template = template.replace('\\\\', '\\')
        #print('template: \n', repr(template))


        try:
            self.textfsm_object = textfsm.TextFSM(io.StringIO(template))
        except Exception as e:
            print(str(e))
            return {'error': str(e)}

        fsm_result = []

        try:
            fsm_result = self.textfsm_object.ParseText(self.data)
        except Exception as e:
            fsm_result = {'error': str(e)}

        #self.data = ''  #set to '' to clear memory
        #print('fsm_result', fsm_result)
        return fsm_result

    def perfmon_parse(self, counter):

        counter_len = len(counter)
        self.df = pd.DataFrame()

        for data_df in self.data:

            columns = list(data_df.columns.values)  #use list() to get list instead of 'numpy.ndarray'

            column = ''
            for c in columns:
                if c[-counter_len:] == counter:   # if right portion of `\\VZ0CAW1\Processor(_Total)\% Processor Time` == `Processor(_Total)\% Processor Time`
                    column = c
                    break

            df = data_df.loc[ : ,[columns[0], column]]   #get all rows, column[0] (timestamp) and column (counter)

            match = re.search(r'^\\\\(.*?)\\', columns[1])  #find the hostname
            hostname = match.group(1)

            df.columns = ['Timestamp', counter]  #change the column namse to "Timestamp" and value of counter

            df.insert(loc=1, column='Hostname', value=hostname)  #Insert the Hostname column with each row containing the hostname

            #Remove the msec from the timestamp and apply the format of 12/08/2017 12:02:11
            #todo: validate the timeformat conversion with other formats
            try:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True).apply(lambda x:x.strftime('%m/%d/%Y %H:%M:%S'))
            except:
                pass

            #append device DF to all dataframes
            self.df = self.df.append(df)


    def get_dataframe(self, data, filter_type):
        if filter_type == 'fk_textfsm':
            self.df = pd.DataFrame(data, columns=self.get_headings(self.textfsm_object.header, title=True))
        else:
            self.df = data

        try:
            self.df['Timestamp'] = pd.to_datetime(self.df['Timestamp'], utc=True).apply(lambda x:x.strftime('%m/%d/%Y %H:%M:%S'))
        except:
            pass

    def clear_dataframe(self):

        self.df = pd.DataFrame()

    def get_graph(self, **kwargs):
        print('get graph kwargs', kwargs)

        testing = kwargs.get('testing', False)   #If testing is True then display returned graph
        df_filter = kwargs.get('filter', None)
        legend = kwargs.get('legend', True)
        index = kwargs.get('index', None)
        data_column = kwargs.get('plot', None)
        interval = kwargs.get('interval', '0')
        try:
            interval = int(interval)
        except:
            interval = 0
        aggregation = kwargs.get('aggregation', '')
        selected_column = kwargs.get('selected', None)
        group_by = kwargs.get('group_by', None)
        start_time = kwargs.get('start_time', '')
        end_time = kwargs.get('end_time', None)

        #print(start_time,end_time)
        hostnames = kwargs.get('hostnames[]', kwargs.get('hostnames', []))
        x_label = kwargs.get('x_label', index)
        #print('original DF:\n', self.df)
        column_mask = []
        path = kwargs.get('path', '')

        if path[-1] != '/':
            path += '/'

        if path[0] == '~':
            path = '{}{}'.format(str(Path.home()), path[1:])

        filename_template = kwargs.get('filename', '')

        if type(hostnames) == type(' '):
            hostnames = [hostnames]

        if selected_column is None:
            return {'error': 'Graph.get_graph() Column to graph is not selected'}
        if data_column is None:
            return {'error': 'Graph.get_graph() Column to plot not selected'}

        if df_filter:
            data_filter = self.df[selected_column] == df_filter
        else:
            data_filter = None

        if hostnames:
            temp = self.df['Hostname'].isin(hostnames)
            data = self.df[temp].copy(deep=True)
        else:
            data = self.df.copy(deep=True)

        try:
            if data_filter:
                data = data[data_filter][data_column].apply(pd.to_numeric)
            else:

                if index:
                    column_mask = [index]
                column_mask += [selected_column, data_column]
                #print(column_mask)
                data = data.loc[:, column_mask]
                #print(data)
                data[data_column] = pd.to_numeric(data[data_column], errors='coerce')
        except Exception as e:
            return {'error': 'Graph.get_graph() Error getting graph data: {}'.format(str(e))}

        if index:
            #todo: determine if index is datetime format

            try:
                data[index] = pd.to_datetime(data[index])
            except:
                pass

            try:
                data.set_index(index, inplace=True)
            except Exception as e:
                print(e)
                return {'error': 'Graph.get_graph() Error setting index: {}'.format(str(e))}


        mask = (data.index >= start_time) & (data.index <= end_time)

        #print(mask)
        #print(data)
        #print(column_mask)
        data = data.loc[mask, :]      #.applymap(lambda x: np.nan if isinstance(x, str) and x.isspace() else x)
        #print(data)


        plt.clf()  #clear plot in case one is left in memory

        if group_by:

            self.fig, self.ax = plt.subplots()   #get figure and axes objects
            self.customize(**kwargs)
            #data.index.name = x_label   #need to do this for the x label since the sx.x_label object doesn't seem to be used

            kwargs['hostname'] = hostnames[0] if hostnames[0] else ''  #generate a hostname incase the filename format uses hostname

            #data = self.process_interval(data, data_column, interval, aggregation)

            #print(data)

            """
            merged_df = None

            for hostname in hostnames:
                temp = data['Hostname'] == hostname
                temp_df = self.process_interval(data[temp], data_column, interval, aggregation)

                print(temp_df)

                if merged_df is None:
                    merged_df = temp_df
                else:
                    merged_df = pd.merge(left=merged_df,right=temp_df, how='left', left_index=True, right_index=True)

            print('merged_df:\n', merged_df)

            grouped = merged_df.groupby(selected_column, as_index=False)[data_column]
            #for group, index in grouped.indices.items():
            #    print('group', group)
            #    print('index', index)
            #    grouped.indices[group] = range(0, len(index))
            grouped.plot(x=x_label, legend=legend)
            """

            df = self.process_interval(data, data_column, interval, aggregation)
            #df = data
            #print(df)
            df.set_index(index, inplace=True)
            df = df.reset_index()  #Remove Timestamp from the index anddrop so that hours can be displayed on graph
            df.drop(df.columns[0], axis=1, inplace=True)
            #print(data)
            #print(df)


            grouped = df.groupby(selected_column)[data_column]
            grouped.plot()


            if path:
                try:
                    filename = filename_template.format(hostname=hostnames[0] if hostnames[0] else '')
                except:
                    filename = hostnames[0] if hostnames[0] else ''
                #print('Saving file {path}{filename}.png'.format(path=path, filename=filename))
                plt.savefig('{path}{filename}.png'.format(path=path, filename=filename))   #, dpi=fig.dpi)
        else:
            count = len(hostnames)
            #print('Hostname count:', count)
            for hostname in hostnames:
                temp = data['Hostname'] == hostname
                temp_df = data[temp]

                #print(temp_df)
                #temp_df.plot(legend=legend)

                #temp_df.drop('Hostname', axis=1, inplace=True)
                #temp_df.reindex([index, data_column])
                #temp_df = temp_df.loc[:,(index,  data_column)]

                self.fig, self.ax = plt.subplots()   #get figure and axes objects

                kwargs['hostname'] = hostname
                self.customize(**kwargs)            # then customize
                #temp_df.index.name = x_label   #need to do this for the x label since the sx.x_label object doesn't seem to be used

                temp_df = self.process_interval(temp_df, data_column, interval, aggregation)

                temp_df.set_index(index, inplace=True)
                temp_df = temp_df.reset_index()  #Remove Timestamp from the index anddrop so that hours can be displayed on graph
                temp_df.drop(temp_df.columns[0], axis=1, inplace=True)

                print(temp_df)

                temp_df.plot(ax=self.ax, legend=legend)

                if path:
                    try:
                        filename = filename_template.format(hostname=hostname)
                    except:
                        filename = hostname

                    plt.savefig('{path}{filename}.png'.format(path=path, filename=filename))   #, dpi=fig.dpi)

                count -= 1

                if count != 0:  #save last graph to return to web page
                    plt.clf()
                    plt.cla()
                    plt.close()

        #plt.show()

        format = r"png"
        sio = io.BytesIO()
        plt.savefig(sio, format=format)
        #print(sio.getvalue())

        if testing:
            plt.show()

        plt.clf()
        plt.cla()
        plt.close()

        return {'data': base64.b64encode(sio.getvalue())}        #.decode('utf-8').replace('\n', '')
        #return base64.b64encode(sio.getvalue())

    def customize(self, **kwargs):

        hostname = kwargs.get('hostname', '')
        title = kwargs.get('title', '')
        y_limit = kwargs.get('y_limit', '0')
        try:
            y_limit = int(y_limit)
        except:
            y_limit = 0
        y_label = kwargs.get('y_label', '')
        y_label_format = kwargs.get('y_label_format', '')
        x_label = kwargs.get('x_label', '')
        grid = kwargs.get('grid', False)

        if type(grid) == type(' '):
            if grid == 'true':
                grid = True
            else:
                grid = False

        try:
            title = title.format(d=kwargs)
        except:
            pass
        self.ax.set_title(title if title else hostname)
        plt.grid(grid)

        if y_limit:
            #print ('Setting y limit:', y_limit)
            plt.ylim((0, y_limit))
            #pass
        if y_label:
            try:
                y_label = y_label.format(d=kwargs)
            except:
                pass
            self.ax.set_ylabel(y_label)
        if x_label:
            try:
                x_label = x_label.format(d=kwargs)
            except:
                pass
            self.ax.set_xlabel(x_label)
        if y_label_format == 'bytes':
            formatter = FuncFormatter(human_readable_bytes)
            self.ax.yaxis.set_major_formatter(formatter)
        elif y_label_format:
            self.ax.yaxis.set_major_formatter(FormatStrFormatter(y_label_format))
            for label in self.ax.get_yticklabels():
                label.set_fontsize(6)

    def process_interval(self, df, data_column, interval, aggregation):
        df = df.reset_index()  #Remove Timestamp from the index anddrop so that hours can be displayed on graph
        #df.drop(df.columns[0], axis=1, inplace=True)

        #print(df)
        #print 'process interval', df.head()
        if df[data_column].dtype == 'object':
            #print 'converting object to float'
            df[data_column] = df[data_column].astype(float)
        if interval > DEFAULT_INTERVAL and interval % DEFAULT_INTERVAL == 0:
            #print('setting agg:', aggregation)
            if aggregation.lower() == 'last':
                df = df.groupby(df.index // (interval // DEFAULT_INTERVAL)).nth(-1)
            elif aggregation.lower() == 'first':
                df = df.groupby(df.index // (interval // DEFAULT_INTERVAL)).nth(0)
            elif aggregation.lower() == 'min':
                df = df.groupby(df.index // (interval // DEFAULT_INTERVAL)).min()
            elif aggregation.lower() == 'max':
                df = df.groupby(df.index // (interval // DEFAULT_INTERVAL)).max()
            elif aggregation.lower() == 'average' or aggregation.lower() == 'mean':
                df = df.groupby(df.index // (interval // DEFAULT_INTERVAL)).mean()
        #print(df)
        return df

    def build_x_axis(self, num_x, **kwargs):
        """

        :param num_x: The number of filtered elements to be plotted
        :param kwargs:
        :return:
        """
        #print 'num_x', num_x
        end_time = kwargs.get('end_time', '')
        start_time = kwargs.get('start_time', '')
        interval = kwargs.get('interval', DEFAULT_INTERVAL)
        max_labels = kwargs.get('max_labels', 0)
        start_time = datetime.strptime(start_time, self.time_format)
        end_time = datetime.strptime(end_time, self.time_format)
        delta_seconds =  (end_time - start_time).total_seconds()
        delta_minutes = delta_seconds / 60
        delta_hours = delta_minutes /  60
        num_x = num_x + 1 if num_x % interval == 0 else num_x
        if max_labels:
            tick_step = int(delta_hours / float(max_labels))    # determine the loop step size
            #print delta_hours, tick_step
            inc_labels = 1 if delta_hours % float(max_labels) else 0   # add one more lable if remainder
            xticks = np.arange(0, num_x, num_x / int(max_labels + inc_labels))  #step by number of elements / number of hour ticks plus 1 (account for 0)
            xlabels = [str(i) for i in range(0, int(delta_hours) + inc_labels + 1, tick_step if tick_step else 1)]
        else:
            xticks = np.arange(0, num_x, num_x / (delta_hours + 1))  #step by number of elements / number of hour ticks plus 1 (account for 0)
            xlabels = [str(i) for i in range(0, int(delta_hours) + 1)]
        #print xticks, xlabels
        return (xticks, xlabels)


if __name__ == '__main__':



    template = '''Value timestamp (.+\d+:\d+:\d+.+\d+)
Value Filldown hostname (\S+)
Value total_calls (.+)


Start
  ^.*Query @ ${timestamp}
  ^${hostname}[>#].*
  ^Total Number of Active Calls : ${total_calls} -> Record'''



    graph_params = {
        'testing': True,
        'index': 'Timestamp',
        'plot': 'Total Calls',
        'selected': 'Hostname',
        'legend': True,
        'path': '~/test_graphs',
        'filename': '{hostanme}',
        'filter': None,
        'interval': '30',
        'aggregation': '',
        'group_by': None,
        'start_time': '05/11/2018 09:34:33',
        'end_time': '05/11/2018 10:16:58',
        'hostnames': 'vz0cube1',
        #'hostname': ['vz0cube1', 'vz0cube2'],
        'x_label': 'Timestamp'
    }


    g = Graph()

    g.get_text_files([PATH + 'CS_vz0cube1.txt', PATH + 'CS_vz0cube2.txt'])

    result = g.textfsm_parse(template)

    g.get_dataframe(result, 'fk_textfsm')

    print('DF Head:\n', g.df.head())
    print('DF Tail:\n', g.df.tail())
    print('DF Length:', len(g.df))

    result = g.get_graph(**graph_params)

    if 'error' in result:
        print(result['error'])


    #format = "png"
    #sio = io.StringIO()
    #plt.savefig(sio, format=format)
    #print(sio.getvalue())


