function scrollingtabbedpanel() {
    //Get the height of the first item
    $('#mask').css({'height':$('#panel-1').height()});

    //Calculate the total width - sum of all sub-panels width
    //Width is generated according to the width of #mask * total of sub-panels
    $('#panel').width(parseInt($('#mask').width() * $('#panel div').length));

    //Set the sub-panel width according to the #mask width (width of #mask and sub-panel must be same)
    $('#panel div').width($('#mask').width());

    //Get all the links with rel as panel
    $('a[rel=panel]').click(function () {

            //Get the height of the sub-panel
            var panelheight = $($(this).attr('href')).height();

            //Set class for the selected item
            $('a[rel=panel]').removeClass('selected');
            $(this).addClass('selected');

            //Resize the height
            $('#mask').animate({'height':panelheight},{queue:false, duration:500});

            //Scroll to the correct panel, the panel id is grabbed from the href attribute of the anchor
            $('#mask').scrollTo($(this).attr('href'), 800);

            //Discard the link default behavior
            return false;
    });
};