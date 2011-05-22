// JavaScript Document
YAHOO.namespace("EMORY_EDU");

//==================================================================================================================
// FUNCTIONS
// uses the "Module Pattern"; a full explanation of this pattern can be found on yuiblog: http://yuiblog.com/blog/2007/06/12/module-pattern
//------------------------------------------------------------------------------------------------------------------
YAHOO.EMORY_EDU = function () {

	//private shorthand references
	var Dom = YAHOO.util.Dom,
		Event = YAHOO.util.Event,
		Anim = YAHOO.util.Anim;

	//private methods

	//==================================================================================================================
	//  UTILS
	//------------------------------------------------------------------------------------------------------------------
	var resetUtilNav = function (elements, links) {
		for(var i in links) {
			Dom.removeClass(links[i], 'active');
		}
		for(var i in elements) {
			Dom.setStyle(elements[i], 'display', 'none');
		}
	};


	//==================================================================================================================
	//  FADES
	//------------------------------------------------------------------------------------------------------------------
	var resetExploreElements = function (elements, links) {
		for(var i in links) {
			Dom.removeClass(links[i], 'active');
		}
		for(var i in elements) {
			if (Dom.getStyle(elements[i], 'opacity') == 1) {
				fadeOutElement(elements[i]);
			}
		}
	};
	
	var initExploreElements = function (elements) {
		for(var i in elements) {
			Dom.setStyle(elements[i], 'opacity', '0');
			Dom.setStyle(elements[i], 'display', 'none');
		}
	};

	var fadeInElement = function (el) {
		Dom.setStyle(el, 'display', 'block');
		var anim = new Anim(el,  { opacity: {from: 0, to: 1 }}, 0.75, YAHOO.util.Easing.easeIn);
		anim.animate();
	};

	var fadeOutElement = function (el) {
		
		function removeDiv() {
			Dom.setStyle(el, 'display', 'none');	
		}
		
		var anim = new Anim(el,  { opacity: {from: 1, to: 0 }}, 0.25, YAHOO.util.Easing.easeIn);
		anim.onComplete.subscribe(removeDiv);
		anim.animate();
	};

	return  {

		init: function () {
			
			//fixIE6flicker
			try {
				document.execCommand('BackgroundImageCache', false, true);
			} catch(e) {}
			
			//init util nav
			this.utilNavLinks = Dom.getElementsByClassName('utilLink', 'a', 'utilityNav');
			this.utilNavFlyouts = Dom.getElementsByClassName('flyOut', 'div', 'utilityNav');

			//init fades
			this.exploreLinks = Dom.getElementsByClassName('exploreLink', 'a', 'exploreTab');
			this.exploreElements = Dom.getElementsByClassName('exploreElement', 'div', 'exploreTab');
			initExploreElements(this.exploreElements);
		
		},

		fadeInExploreElement: function (el, linkClicked) {
			resetExploreElements(this.exploreElements, this.exploreLinks);
			Dom.addClass(linkClicked, 'active');
			this.activeLink = linkClicked;
			fadeInElement(el);
		},

		closeElement: function (el) {
			resetExploreElements(this.exploreElements, this.exploreLinks);
		},

		activateLink: function (el) {
			Dom.addClass(el, 'active');
		},
		
		deActivateLink: function (el) {
			if (el != this.activeLink) {
				Dom.removeClass(el, 'active');
			}
		},

		showUtilNav: function (el) {
			resetUtilNav(this.utilNavFlyouts, this.utilNavLinks);
			var utilLink = Dom.getElementsByClassName('utilLink', 'a', el)[0];
			var flyOut = Dom.getElementsByClassName('flyOut', 'div', el)[0];
			Dom.addClass(utilLink, 'active');
			Dom.setStyle(flyOut, 'display', 'block');			
		},
		
		closeUtilNav: function (el) {
			resetUtilNav(this.utilNavFlyouts, this.utilNavLinks);
		}

	};
}(); // the parens here cause the anonymous function to execute and return