
var graphId = -1;
var filter_data = '';
var filter_type = '';
var file_info = [];
var df_columns = [];

var index_column = '';
var data_column = '';
var device_column = '';
var column_selects = ['index_col', 'selected_col', 'plot_col'];
var checkboxes = ['legend', 'group_by', 'save_datetime'];
var textInputs = ['y_label', 'y_label_format', 'y_limit', 'x_label', 'interval', 'aggregation','title'];

$("#get-pandas").prop("disabled", true);
$("#gen-graph").prop("disabled", true);
$("#auto-graph").prop("disabled", true);
$("#save-options").prop("disabled", true);

disableGraphOptions();

var graphOptions = {}
var havePandasDF = false;


$(function() {
	//$('.datetimepicker').datetimepicker('destroy');
    $('.datetimepicker').datetimepicker({
    	format: 'mm-dd-yyyy hh:ii',
    	autoclose: true,
    })
        .on('changeDate', function(e) {
        // `e` here contains the extra attributes

    	var key = $(e.target).attr('id');  //get datetimepicker ID
    	//console.log('changeDate', key);

        var date = $('.datetimepicker').datetimepicker('getDate'); //get updated datetime
        //console.log('New date:', date);
        graphOptions[key] = date;  //saveinto graph options
        $("#save-options").prop("disabled", false);
    });
    //$('.datetimepicker').datetimepicker('clearDates');
  });





//reset graph options to default
function resetGraphOptions() {
	graphOptions = {
		selected: null,	//device column
		plot: null,		//data column name - y axis
		filter: null,
		legend: true,	//display legend
		index: null,    //index column name - x axis
		group_by: true, //group by device column to combine into one graph
		id: -1,
		hostnames: [],   //selected server names
		path: '~/graphs',
		filename: '{hostname}',
        title: '',
        y_limit: '',
        y_label: '',
        y_label_format: '',
        x_label: '',
        grid: false,
        end_time: '',
        start_time: '',
        interval: '',
        aggregation: '',
        max_labels: 0,
        start_time: '',
        end_time: '',
        pandas_start_time: '',
        pandas_end_time: '',
        save_datetime: false,



	}
}

function updateFilePaths() {
	$('#file-path').val(graphOptions.path);
	$('#file-template').val(graphOptions.filename);
}

//update graphOptions variable with web page selections
function trackGraphOptions() {

	//console.log('update', graphOptions);

	for (i = 0; i < column_selects.length; i++) {
		data = column_selects[i];
		select_val = $('#' + data + '_sel').val();
		if (select_val === '') {
			graphOptions[data.split('_', 1)[0]] = null;
		} else {
			graphOptions[data.split('_', 1)[0]] = select_val;
		}
	}

	for (i = 0; i < checkboxes.length; i++) {
		data = checkboxes[i];
		//console.log(data, $('#' + data).prop("checked"));
		graphOptions[data] = $('#' + data).prop("checked");
	}

	graphOptions.path = $('#file-path').val();
	graphOptions.filename = $('#file-template').val();

	var hostnames = serversTable.rows( { selected: true } ).data().pluck(0).toArray();
	//console.log('tacking hostnames', hostnames);
	graphOptions.hostnames = hostnames;
	//console.log('updated', graphOptions);


}

//save graphOptions variable to DB
function saveGraphOptions() {

	pkid = table.rows( {selected: true} ).data().pluck( 'DT_RowId' )[0];
	//console.log(pkid, graphOptions);
	var temp = graphOptions;
	delete temp['hostnames'];

	if ( !graphOptions.save_datetime ) {
		console.log('clearing date time before saving');
		temp.end_time = '';
		temp.start_time = '';
	}

	jsonOptions = JSON.stringify(temp);
  jsonOptions = $.fn.dataTable.util.escapeRegex(jsonOptions);
    $.ajax({
      url: 'save_graph_options',
      data: {'pkid': pkid, 'graph_options': jsonOptions},
      type: 'post',
      success: function (json) {
      	//console.log('save options json response', json);
		$("#save-options").prop("disabled", true);
		//$('.save-range').prop( "checked", false);
		var data = table.row( {selected: true} ).data();
		//console.log(data);

		data.main.graph_options = jsonOptions  //update table data with saved graph options
		//console.log(data);
      }
    });
}


//retrieve graph info from DB
function getGraphInfo(data) {
	data.graph_id = graphId;
	//console.log('graph info param', data);
    $.ajax({
      url: 'get_graph_info',
      data: data,
      type: 'post',
      success: function (json) {
        data = JSON.parse(json);

        //console.log('graph info data', data);

        filesTable.rows.add( data.files ).draw();

        //set global variables
        filter_type = data.filter_type
        filter_data = data.filter_data

       	//update Pandas Filter table with small desc and filter data
		$('#pandas-filter-div').append('<code id="pandas-filter-code">' + data.filter_data + '</code>');
		$('#pandas-filter-desc-small').html(data.filter_desc);


		graphId = data.graph;  //track graph process ID
		file_info = data.files;

		//console.log(files);
		//$("#get-pandas").prop("disabled", false);
      }
    });
}

//Update select options to highlight selected and disable options selected in other DDL
function updateSelectOptions() {
	var disable = {}

	//build initial object to contain options to disable
	for (c = 0; c < column_selects.length; c++) {
		disable[column_selects[c] + '_sel'] = [];
	}

	for (c = 0; c < column_selects.length; c++) {
		graphOptKey = column_selects[c].split('_', 1)[0];
		graphOpt = graphOptions[graphOptKey]

		//apply selected option
		$('#' +  column_selects[c] + '_sel').val(graphOpt);

		//build array for each select of disabled options
		for (d in disable) {
			//but only for the other selects
			if (d != graphOptKey + '_col_sel') {
				disable[d].push(graphOpt);
			}
		}
	}

	//reset all options to enabled
	$(".column-defs option").prop('disabled', false);

	for (d in disable) {
		//for each select (d) loop through and  disable each option in the array
		for (i = 0; i < disable[d].length; i++) {
			opt = disable[d][i];
			//some values are null, ignore those
			if (opt) {
				$('#' + d + ' option[value="' + opt.replace(/\\/g, "\\\\") + '"]').prop('disabled', true);
			}
		}
	}

}

//remove pandas dataframe and remove process ID from Python
//used when reloading or closing web page
function clearGraph(data) {
    $.ajax({
      url: 'clear_graph',
      data:  {'id': graphId, 'kill': data} ,
      type: 'post',
    });
}


function populateServers(data) {
	serversTable.clear();
	for (i=0; i < data.length; i++) {
		serversTable.row.add([data[i]]);
	}
	serversTable.draw();
}

function populateDatetime() {
	//$('.datetimepicker').datetimepicker('clearDates');

	var start_time = graphOptions.start_time;
	var end_time = graphOptions.end_time;
	//console.log('Datetime from DB:', start_time, end_time);
	if (start_time !== '' && end_time !== '') {
		//console.log('converting string to date object');
		start_time = new Date(start_time);
		end_time = new Date(end_time);
		if ( havePandasDF ) {
			var pandas_start_time = graphOptions.pandas_start_time;
			var pandas_end_time = graphOptions.pandas_end_time;

			var minutes = 5;
			if (pandas_start_time  !== '') {
				pandas_start_time = new Date(pandas_start_time);
				$('.datetimepicker').datetimepicker('setStartDate', new Date(pandas_start_time.getTime() - minutes*60000));
			}
			if (pandas_end_time  !== '') {
				pandas_end_time = new Date(pandas_end_time);
				$('.datetimepicker').datetimepicker('setEndDate', new Date(pandas_end_time.getTime() + minutes*60000));
			}
		}
	} else {
		//console.log('setting datetime to blank');
		start_time = '';
		end_time = '';
		$('.datetimepicker').datetimepicker('setStartDate', null);
		$('.datetimepicker').datetimepicker('setEndDate', null);

	}

	//console.log('updating inputs with', start_time, end_time);
	$('#start_time').datetimepicker('update', start_time);
	$('#end_time').datetimepicker('update', end_time);


	//show and hide is a workaround for the datepicker showing multiple pickers on first showing
	$('.datetimepicker').datetimepicker('show');
	$('.datetimepicker').datetimepicker('hide');

}

//build column graph options DDL
//includes event handlers and marking selected options and disabling
//options selected from other DDL
function buildColumnSelects() {

	for (c = 0; c < column_selects.length; c++) {
		var select = $('<select class="column-defs" id="' +  column_selects[c] + '_sel"><option value="">Select Index:</option></select>')
			.appendTo( $('#' + column_selects[c]).empty() )
			.off()
			.on ('change', function() {
				select_id = $(this).attr('id').split('_', 1)[0];
				select_val = $(this).val();
				//console.log('select_val', select_val);

				//update graphOptions variable
				trackGraphOptions();
				//console.log('select_id', select_id);

				//sync up group by checkbox with name of selected option
				if (select_id === 'selected') {
					syncGroupBy();
				}

				//update each of the DDL
				updateSelectOptions();

				//enable the save button
				$("#save-options").prop("disabled", false);

			} );

		//build DDL options
		for (i = 0; i < df_columns.length; i++) {
			col_name = df_columns[i]

			if (col_name != index_column) {
				select.append( '<option value="'+ col_name +'">'+ col_name +'</option>' );
			}
		}

	}

	//update initial DDL with selected option and disabled options
	updateSelectOptions();


}

//update checkboxes based on current graphOptions variable - likely from DB
function buildCheckboxes() {
	//$('.graph-cb').attr('checked', false);
	for (i = 0; i < checkboxes.length; i++) {
		//console.log(checkboxes[i], graphOptions[checkboxes[i]]);
		$('#' + checkboxes[i]).prop('checked', graphOptions[checkboxes[i]]);
	}
}

function populateTextInputs() {
	for (i=0; i < textInputs.length; i++) {
		$('#' + textInputs[i]).val(graphOptions[textInputs[i]]);
	}
}

function syncGroupBy () {

	//enable checkbox
	$("#group_by").prop("disabled", false);
	//get device column selection
	var device_column = $('#selected_col_sel').val()
	//console.log('sync', $('#selected_col_sel').val());

	if (device_column === '') {
		//if null and row is selected then indicate no device selected
		if (table.row( { selected: true } ).any()) {
			groupBy = 'Group By (Device Col not selected)';
			cb_disabled = true; //make sure to uncheck group by checkbox
		//otherwise just display group by if no row selection
		} else {
			groupBy = 'Group By';
			cb_disabled = false;  //display default option
			$("#group_by").prop("disabled", true); //disable checkbox if no row selection
		}

	} else {
		//display the device column name
		groupBy = 'Group By ' + device_column;
		cb_disabled = false;
	}


	if (cb_disabled) {
		//uncheck if device option not selected
		$('#group_by').attr('checked', false);
	} else {
		//otherwise show configured checkbox status
		$('#group_by').attr('checked', graphOptions['group_by']);
	}

	//save the checkbox status
	graphOptions['group_by'] = $('#group_by').prop('checked');

	//update the label span display
	$('#group_by_label span').text(groupBy);
}

$('#save-options').click(function(){
	trackGraphOptions();
	saveGraphOptions();
	//$('#save-options').addClass('active');
	//$('#save-options').attr('aria-pressed', 'false');

	$("#save-options").prop("disabled", true);
} );


function generate_dataframe(autoGraph) {
	$("#get-pandas").prop("disabled", true);
  	var startTime = Date.now();
 	$( "code" ).remove( "#pandas-code" );
 	$("#gen-graph").prop("disabled", true);
 	$("#auto-graph").prop("disabled", true);

 	$('#graph-desc-small').html('');
 	$('#graph-div').empty();
 	$('#pandas-desc-small').html('Processing please wait');
	console.log(filter_data);
	web_files = [];
	for (i = 0; i < file_info.length; i++) {
		web_files.push(file_info[i].web_path);
	}
    $.ajax({
      url: 'get_dataframe',
      data: {'id': graphId, 'files': web_files, 'filter_data': filter_data, 'filter_type': filter_type},
      type: 'post',
      error: function (data) {
      	$('#pandas-div').append('<code id="pandas-code">Status Code: ' + data.status + '<br>' + data.statusText + '</code>');
      	$('#pandas-desc-small').html('Error processing data');
      	$("#gen-graph").prop("disabled", true);
      	$("#auto-graph").prop("disabled", true);

      },
      success: function (json) {
        data = JSON.parse(json);

        if (data.hasOwnProperty('error')) {
      		$('#pandas-div').append('<code id="pandas-code">Error: ' + data.error + '</code>');
      		$('#pandas-desc-small').html('Error processing data');
      		$("#gen-graph").prop("disabled", true);
      		$("#auto-graph").prop("disabled", true);

        } else {
        	havePandasDF = true;
        	df_columns = data.columns;
        	buildColumnSelects();
        	buildCheckboxes();
        	populateTextInputs();
        	syncGroupBy();
        	populateServers(data.hostnames);

			if ( !graphOptions.save_datetime ) {
				graphOptions.start_time = data.start_time;
				graphOptions.end_time = data.end_time;
			}
			graphOptions.pandas_start_time = data.start_time;
			graphOptions.pandas_end_time = data.end_time;
			populateDatetime();

        	if (autoGraph) {

        		disableGraphOptions();

				$('#pandas-div').append('<code id="pandas-code">' + data.df_head + '</code>');
				$('#pandas-desc-small').html('Took ' + ((Date.now() - startTime) / 1000) + ' seconds to process<br>Showing top and bottom 5 rows of ' + data.df_length + ' rows');

				generate_graphs(true);

        	} else {
				$('#pandas-div').append('<code id="pandas-code">' + data.df_head + '</code>');
				$('#pandas-desc-small').html('Took ' + ((Date.now() - startTime) / 1000) + ' seconds to process<br>Showing top and bottom 5 rows of ' + data.df_length + ' rows');

				enableGraphButton();
				enableGraphOptions();
			}


		}
		$("#get-pandas").prop("disabled", true);

      }
    });

}

function generate_graphs(autoGraph) {
	if (autoGraph) {
		$('.select-all-devices').prop( "checked", false );
		$('#select-all').prop( "checked", true);
		serversTable.rows().select();
	}

  	var startTime = Date.now();
 	$('#graph-div').empty();
 	$("#gen-graph").prop("disabled", true);
 	$("#auto-graph").prop("disabled", true);

 	$('#graph-desc-small').html('Processing please wait');

 	trackGraphOptions();
 	graphOptions.id = graphId;
 	//console.log('Getting graph using: ', graphOptions);

    $.ajax({
      url: 'get_pd_graph',
      data: graphOptions,
      type: 'post',
      error: function (data) {
      	$('#graph-div').append('<code id="graph-code">Status Code: ' + data.status + '<br>' + data.statusText + '</code>');
      	$('#graph-desc-small').html('Error processing data');
      	$("#gen-graph").prop("disabled", true);
      	$("#auto-graph").prop("disabled", true);

      },
      success: function (data) {
        //data = JSON.parse(json);

		//console.log(data);
		//$('#pandas-div').append('<code id="pandas-code">' + data.df_head + '</code>');

		$('#graph-div').empty().append(data);


		$('#graph-desc-small').html('Took ' + ((Date.now() - startTime) / 1000) + ' seconds');

		enableGraphButton();
		enableGraphOptions();

      }
    });

}

$('#get-pandas').click(function(){

	generate_dataframe(false);

} );


$('#auto-graph').click(function(){

	$("#get-pandas").prop("disabled", true);
	generate_dataframe(true);


} );


window.onbeforeunload = closingCode;
function closingCode(){
   clearGraph(true);
   return null;
}

//enable graph options
function enableGraphOptions() {
    $('.column-defs').attr('disabled', false);
	$('.graph-cb').prop("disabled", false);
	$('.select-all-devices').prop("disabled", false);
	$('.file-opts').prop("disabled", false);
	$('.input-opts').prop("disabled", false);
	$('.picker-input').prop("disabled", false);
	$('.save-range').prop("disabled", false);
}

//disable graph options
function disableGraphOptions() {
    $('.column-defs').attr('disabled', true);
	$('.graph-cb').prop("disabled", true);
	$('.select-all-devices').prop("disabled", true);
	$('.file-opts').prop("disabled", true);
	$('.input-opts').prop("disabled", true);
	$('.picker-input').prop("disabled", true);
	$('.save-range').prop("disabled", true);

}

//enable generate graph button only if Servers are selected
function enableGraphButton() {
	var count = serversTable.rows( { selected: true } ).count();
	//console.log('enableGraphButton() count', count);

	if (count > 0) {
		$("#gen-graph").prop("disabled", false);
	} else {
		$("#gen-graph").prop("disabled", true);
	}
}

$('#gen-graph').click(function(){

	generate_graphs(false);

} );



var filesTable = $('#files-table').DataTable({
	scrollY: "200px",
	dom: 'ti',
	paging: false,
	columns: [
		{data: 'filename'},
		{data: 'filesize'},
		{data: 'timestamp'}
	],
	columnDefs: [
		{
			targets: 0,
			type: 'natural'
		}
	]
});

var serversTable = $('#servers-table').DataTable({
	scrollY: "200px",
	dom: 'ti',
	paging: false,
	select: {style: 'multi+shift'},
	columnDefs: [
		{
			targets: 0,
			type: 'natural'
		}
	]
});




function clearPanels () {
    	filesTable.clear().draw();
    	serversTable.clear().draw();
 		clearGraph();

 		df_columns = [];
 		resetGraphOptions();
 		buildColumnSelects();
 		$( "code" ).remove( "#pandas-filter-code" );
 		$( "code" ).remove( "#pandas-code" );
 		$('#pandas-filter-desc-small').html('');
 		$('#pandas-desc-small').html('');
		$("#get-pandas").prop("disabled", true);
		$("#save-options").prop("disabled", true);

		$('#graph-div').empty()
		$('#graph-desc-small').html('Complete');
		$("#gen-graph").prop("disabled", true);
		$("#auto-graph").prop("disabled", true);

		$('.column-defs').attr('disabled', true);
		$('.graph-cb').prop("disabled", true);

		$('.select-all-devices').prop("disabled", true);
		$('.select-all-devices').prop( "checked", false );
}

table.on( 'select', function ( e, dt, type, indexes ) {
    if ( type === 'row' ) {
    	resetGraphOptions();  //set graphOptions to default
    	havePandasDF = false;
        var data = table.rows( indexes ).data().pluck( 'main' );  //get the table data
        //console.log('selected row data', data[0].graph_options);
        clearPanels();  //clear the panels
        $("#get-pandas").prop("disabled", false);  //enable generate pandas button
        $("#auto-graph").prop("disabled", false);  //enable auto generate graphs button
        getGraphInfo(data[0]);  //get the graph options for selected graph

        //console.log('data[0].graph_options', data[0].graph_options);

        //sqlite3 escapes {} wwhen storing in DB
        var temp_options = data[0].graph_options;
        temp_options = temp_options.replace(/\\/g, '');
        console.log(temp_options);
        db_options = JSON.parse(temp_options);
        console.log(db_options);
        graphOptions = Object.assign(graphOptions, db_options);  //combine the default graph options with saved options

        //console.log('db_options', db_options);
        //console.log('graphOptions', graphOptions);

        df_columns = [];
		for (c = 0; c < column_selects.length; c++) {
			opt = graphOptions[column_selects[c].split('_', 1)[0]]

			if (opt) {
				df_columns.push(opt)  //set selected option to the saved option for graph columns (index, device, data)
			}
		}


        buildColumnSelects();  //Build the options and disable selected
        buildCheckboxes();
        populateTextInputs();
        updateFilePaths();
        syncGroupBy();			//sync Group By check box and label display with saved options
        populateDatetime();

		$('.column-defs').attr('disabled', true);
		$('.graph-cb').prop("disabled", true);

    }
} );


table.on( 'deselect', function ( e, dt, type, indexes ) {
    if ( type === 'row' ) {
    	havePandasDF = false;
    	clearPanels();
    	syncGroupBy();
    	resetGraphOptions();

    }
} );

//code for automatically selecting graph for testing
//table
//    .on( 'init.dt', function () {
//        table.row(6).select();


//    } );


$('input.graph-cb').on('change', function () {
	$("#save-options").prop("disabled", false);
});

$('input.file-opts').on('change', function () {
	$("#save-options").prop("disabled", false);
});


$('input.input-opts').on('change', function () {
	console.log('input change');
	var id = $(this).prop('id');
	graphOptions[id] = $(this).val();
	$("#save-options").prop("disabled", false);
	console.log(graphOptions);
});



$('input.save-range').on('change', function () {
	var cb = $(this).val();
	graphOptions[cb] = $('#' + cb).prop( "checked");
	$("#save-options").prop("disabled", false);
	//console.log(graphOptions);
	//populateDatetime();
});



$('input.select-all-devices').on('change', function () {
	var cb = $(this).val();
	$('.select-all-devices').prop( "checked", false );
	$('#' + cb).prop( "checked", true);

	if (cb === 'select-all') {
        serversTable.rows().select();
	} else {
		serversTable.rows().deselect();
	}
});


serversTable.on( 'select deselect', function ( e, dt, type, indexes ) {
    if ( type === 'row' ) {
        enableGraphButton();
    }
});

serversTable.on( 'user-select', function ( e, dt, type, indexes ) {

	$('.select-all-devices').prop( "checked", false );

});



//Editor config

    // Activate an inline edit on click of a table cell
    $('#main-table').on( 'click', 'tbody td:not(:first-child)', function (e) {


    	var cellIndex = table.cell(this).index().column;
    	var title = $(table.column(cellIndex).header()).text();

    	var row = $(this).closest('tr');
    	var data = table.row($(row)).data();
		var graphSource = data.source.title;

		var graphFilter = $(this).hasClass('graph-filter');

		if ((graphFilter && graphSource === title) || !graphFilter) {
	        editor.inline( this, {
    	        onBlur: 'submit',
        	} );
        }
        table.row($(row)).deselect();  //deselect row to make sure user re-selects to refresh graph options section
    } );


    // Display the buttons
    new $.fn.dataTable.Buttons( table, [
        { extend: "create", editor: editor },
        { extend: "edit",   editor: editor },
            {
                extend: "selectedSingle",
                text: 'Duplicate',
                action: function ( e, dt, node, config ) {
                    // Place the selected row into edit mode (but hidden),
                    // then get the values for all fields in the form
                    var values = editor.edit(
                            table.row( { selected: true } ).index(),
                            false
                        )
                        .val();

                    // Create a new entry (discarding the previous edit) and
                    // set the values from the read values
                    editor
                        .create( {
                            title: 'Duplicate record',
                            buttons: 'Create from existing'
                        } )
                        .set( values );
                }
            },
        { extend: "remove", editor: editor }
    ] );

    table.buttons().container()
        .appendTo( $('.col-sm-6:eq(0)', table.table().container() ) );



editor.dependent( 'main.fk_graph_sources', function ( val, data, callback ) {
	//console.log('dependent');
    if (val == '1') {
    	var depend = { show: 'main.fk_textfsm', hide: 'main.fk_perfmon_counters'};
    	return depend;

    } else if (val == '2') {
    	var depend = { hide: 'main.fk_textfsm', show: 'main.fk_perfmon_counters'};
    	return depend;

    } else {
    	return { hide: ['main.fk_perfmon_counters', 'main.fk_textfsm']}
    }
} );


    editor
        .on( 'postCreate postRemove', function () {
            // After create or edit, a number of other rows might have been effected -
            // so we need to reload the table, keeping the paging in the current position
		    table.rows().deselect();  //remove selection and more importantly the Graph Options selection
            table.ajax.reload( null, false );
        } )
        .on( 'initCreate', function () {
            // Enable order for create
            editor.field( 'main.pkid' ).disable();
        } )
        .on( 'initEdit', function () {
        //console.log('initEdit');
            // Disable for edit (re-ordering is performed by click and drag)
            editor.field( 'main.pkid' ).disable();
        } );


editor.on( 'preSubmit', function (e, action) {
	//console.log('preSubmit action', action);
	//console.log('original graph_options',editor.field( 'main.graph_options' ).val());
  if ( action.action == 'create' ) {
  	if (action.data[0].main.graph_options.length == 0) {
		var temp = graphOptions;
		delete temp['hostnames'];
    	action.data[0].main.graph_options = JSON.stringify(temp);
    }

    action.data[0].main.graph_options = $.fn.dataTable.util.escapeRegex(action.data[0].main.graph_options);
    table.rows().deselect();  //remove selection and more importantly the Graph Options selection
  }
} );


//Build initial default page display
resetGraphOptions();
buildColumnSelects();
buildCheckboxes();
populateTextInputs();
updateFilePaths();
