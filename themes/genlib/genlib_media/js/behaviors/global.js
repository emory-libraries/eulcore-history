/* 
* global page behavior initialization for
*/

//For utility menu
YAHOO.util.Event.onDOMReady(YAHOO.EMORY_EDU.init, YAHOO.EMORY_EDU, true);

// jQuery initialization
$(document).ready(function(){
	// tabbed search
	$('div.view-tabbed-search-header div.views-field-field-tooltip-value .field-content a').click( function() {
		var el = $(this).parents('li');
		el.addClass('active');
		el.siblings('li').removeClass('active');
		return false;
	});
	/* disabled by request
	$('div.view-tabbed-search-header li.views-row .field-content a').hover( 
		//.tooltip is the next element next
		function() { $(this).next().show(); $('#block-views-tabbed_search_header-block_1').css('z-index','9999'); },
		function() { $(this).next().hide(); $('#block-views-tabbed_search_header-block_1').css('z-index','1'); }
	);
	*/
	// turn on the first item
	$('div.view-tabbed-search-header li.views-row-first .field-content a').click();
	// remove the row first class
	$('div.view-tabbed-search-header li.views-row-first').removeClass('views-row-first');
	
	// tabbed search in the body
	$('div.view-tabbed-search-body li.views-row .views-field-field-tooltip-value .field-content a').click( function() {
		var el = $(this).parents('li');
		el.addClass('active');
		el.siblings('li').removeClass('active');
		return false;
	});
	/* no tooltips in the body tabbed search
	$('div.view-tabbed-search-body li.views-row .views-field-field-tooltip-value .field-content a').hover( 
		//.tooltip is the next element next
		function() { $(this).next().show(); },
		function() { $(this).next().hide(); }
	);
	*/
	// add alt text for the site search if it's not there already
	var siteSearchInput = $('div.view-tabbed-search-header .tabbed_site_search input:text');
	if (siteSearchInput.attr('alt') == ''){
		siteSearchInput.attr('alt', 'Search this Site');
	}
	
	// make inputs use inputTip
	$('div.view-tabbed-search-header input:text').inputTip();
	$('div.view-tabbed-search-body input:text').inputTip();
	// turn on the first tabbed search item
	$('div.view-tabbed-search-body li.views-row-first .field-content a').click();
	// remove the row first class
	$('div.view-tabbed-search-body li.views-row-first').removeClass('views-row-first');
	
	// make any input with the class into an inputTip
	$('input.inputTip').inputTip();
	// make all external links and external forms open in a new window
	// NOTE: may need to do some exclusions and domain name sniffing
	$("#content a[href^='http']").attr('target','_blank').attr('rel','external');	// make any link pointing to http open external
	var curDomain = document.domain;	// switch back both http and https links
	$("#content a[href^='http://"+curDomain+"'][rel=external]").attr('rel','internal').removeAttr('target');	// now correct that - strip ones that are to this domain
	$("#content a[href^='https://"+curDomain+"'][rel=external]").attr('rel','internal').removeAttr('target');	// now correct that - strip ones that are to this domain
	// do the same for forms
	$("form [action^='http']").attr('target','_blank');
	$("form [action^='http://"+curDomain+"']").removeAttr('target');
	$("form [action^='https://"+curDomain+"']").removeAttr('target');
	
	/* Tabbed Box */
	$('#tabbed-box > ul').tabs({ fx: { height: 'toggle', opacity: 'toggle' } }); //Swipe
	//$('#tabbed-box > ul').tabs({ fx: { height: 'show', opacity: 'hide' } }); //Swap

});

