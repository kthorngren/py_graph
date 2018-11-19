 	
 	// Update checkbox during inline editing
    $('#main-table').on( 'change', 'input.editor-enabled', function () {
    	//console.log('enabled change', $(this).prop( 'checked' ) ? 1 : 0);
        editor
            .edit( $(this).closest('tr'), false )
            .set( 'main.enabled', $(this).prop( 'checked' ) ? 1 : 0 )
            .submit();
    } );
    $('#main-table').on( 'change', 'input.editor-toggle', function () {
    	//console.log('toggle change', $(this));
        editor
            .edit( $(this).closest('tr'), false )
            .set( 'main.toggle', $(this).prop( 'checked' ) ? 1 : 0 )
            .submit();
    } );



    // Activate an inline edit on click of a table cell - row select and checkboxes
    $('#main-table').on( 'click', 'tbody td:not(:first-child, :nth-child(4), :nth-child(5) )', function (e) {
        	//console.log('inline');

        editor.inline( this, {
            onBlur: 'submit',
        } )
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


    editor
        .on( 'postCreate postRemove', function () {
            // After create or edit, a number of other rows might have been effected -
            // so we need to reload the table, keeping the paging in the current position
            table.ajax.reload( null, false );
        } )
        .on( 'initCreate', function () {
            // Enable order for create
            editor.field( 'main.pkid' ).disable();
        } )
        .on( 'initEdit', function () {
            // Disable for edit (re-ordering is performed by click and drag)
            editor.field( 'main.pkid' ).disable();
        } )
