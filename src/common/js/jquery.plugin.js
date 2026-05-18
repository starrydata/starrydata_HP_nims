
/* Experts Table
-------------------------------------------------------------------------------------------------------- */  
$(function() {
     $("body#experts table.tbl_gray tr td:empty").parent("tr").remove();
});



/* For jquery.heightLine.js
-------------------------------------------------------------------------------------------------------- */
//使い方 https://blog.webcreativepark.net/2013/10/21-112000.html
//サンプル
//$(".box0>div").heightLine();

//
//$(".box_contents_list h2").heightLine({
//    minWidth: 769
//});







/* For modaal.js
-------------------------------------------------------------------------------------------------------- */
$('.detail_img').modaal({
    type: 'image'
});



/* Global Navi Megamenu.js
-------------------------------------------------------------------------------------------------------- */
/*global $ */
$(document).ready(function () {

    "use strict";

    $('.menu > ul > li:has( > ul)').addClass('menu-dropdown-icon');
    //Checks if li has sub (ul) and adds class for toggle icon - just an UI


    $('.menu > ul > li > ul:not(:has(ul))').addClass('normal-sub');
    //Checks if drodown menu's li elements have anothere level (ul), if not the dropdown is shown as regular dropdown, not a mega menu (thanks Luka Kladaric)

    $(".menu > ul").before("<a href=\"#\" class=\"menu-mobile\"> </a>");

    //Adds menu-mobile class (for mobile toggle menu) before the normal menu
    //Mobile menu is hidden if width is more then 959px, but normal menu is displayed
    //Normal menu is hidden if width is below 959px, and jquery adds mobile menu
    //Done this way so it can be used with wordpress without any trouble

    $(".menu > ul > li").hover(
        function (e) {
            if ($(window).width() > 943) {
                $(this).children("ul").fadeIn(150);
                e.preventDefault();
            }
        }, function (e) {
            if ($(window).width() > 943) {
                $(this).children("ul").fadeOut(150);
                e.preventDefault();
            }
        }
    );
    //If width is more than 943px dropdowns are displayed on hover


    //the following hides the menu when a click is registered outside
    $(document).on('click', function(e){
        if($(e.target).parents('.menu').length === 0)
            $(".menu > ul").removeClass('show-on-mobile');
    });

    $(".menu > ul > li").click(function() {
        //no more overlapping menus
        //hides other children menus when a list item with children menus is clicked
        var thisMenu = $(this).children("ul");
        var prevState = thisMenu.css('display');
        $(".menu > ul > li > ul").fadeOut();
        if ($(window).width() < 943) {
            if(prevState !== 'block')
                thisMenu.fadeIn(150);
        }
    });
    //If width is less or equal to 943px dropdowns are displayed on click (thanks Aman Jain from stackoverflow)

    $(".menu-mobile").click(function (e) {
    $(".menu-mobile").toggleClass('active'); //active付与で、アイコン切り替え
        $(".menu > ul").toggleClass('show-on-mobile');
        e.preventDefault();
    });
    //when clicked on mobile-menu, normal menu is shown as a list, classic rwd menu story (thanks mwl from stackoverflow)

});





/* Opacity Rollover
-------------------------------------------------------------------------------------------------------- */

/*=====================================================
meta: {
  title: "jquery-opacity-rollover.js",
  version: "2.1",
  copy: "copyright 2009 h2ham (h2ham.mail@gmail.com)",
  license: "MIT License(http://www.opensource.org/licenses/mit-license.php)",
  author: "THE HAM MEDIA - http://h2ham.seesaa.net/",
  date: "2009-07-21"
  modify: "2009-07-23"
}
=====================================================*/
(function($) {
	
	$.fn.opOver = function(op,oa,durationp,durationa){
		
		var c = {
			op:op? op:1.0,
			oa:oa? oa:0.8,
			durationp:durationp? durationp:'fast',
			durationa:durationa? durationa:'fast'
		};
		

		$(this).each(function(){
			$(this).css({
					opacity: c.op,
					filter: "alpha(opacity="+c.op*100+")"
				}).hover(function(){
					$(this).fadeTo(c.durationp,c.oa);
				},function(){
					$(this).fadeTo(c.durationa,c.op);
				})
		});
	},
	
	$.fn.wink = function(durationp,op,oa){

		var c = {
			durationp:durationp? durationp:'slow',
			op:op? op:1.0,
			oa:oa? oa:0.2
		};
		
		$(this).each(function(){
			$(this)	.css({
					opacity: c.op,
					filter: "alpha(opacity="+c.op*100+")"
				}).hover(function(){
				$(this).css({
					opacity: c.oa,
					filter: "alpha(opacity="+c.oa*100+")"
				});
				$(this).fadeTo(c.durationp,c.op);
			},function(){
				$(this).css({
					opacity: c.op,
					filter: "alpha(opacity="+c.op*100+")"
				});
			})
		});
	}
	
})(jQuery);


// 設定クラス
$(function(){
  $('.btn_over').opOver();
});





/* Smooth Scroll
-------------------------------------------------------------------------------------------------------- */

jQuery.fn.extend({
  scrollTo : function(speed, easing) {
    <!-- hashの取得が出来なければ、処理を中断 -->
    if(!$(this)[0].hash || $(this)[0].hash == "#") {
      return false;
    }
    return this.each(function() {
		//topに-100、とすることで、フロートナビ用の高さを確保
      var targetOffset = $($(this)[0].hash).offset().top-400;
      $('html,body').animate({scrollTop: targetOffset}, speed, easing);
    });
  }
});

$(document).ready(function(){
  $('a[href*=#]').click(function() {
    $(this).scrollTo(1000);
    return false;
  });
});





/* Pagetop
-------------------------------------------------------------------------------------------------------- */
$(function() {
	var topBtn = $('#pagetop');	
	topBtn.hide();
	//スクロールが100に達したらボタン表示
	$(window).scroll(function () {
		if ($(this).scrollTop() > 100) {
			topBtn.fadeIn();
		} else {
			topBtn.fadeOut();
		}
	});
	//スクロールしてトップ
    topBtn.click(function () {
		$('body,html').animate({
			scrollTop: 0
		}, 500);
		return false;
    });
});






/* #timeout
-------------------------------------------------------------------------------------------------------- */
if (window.matchMedia( "(max-width: 768px)" ).matches) {
/* ウィンドウサイズが 768px以下の場合のコードをここに */
$(document).ready(function() {
         //queue()で処理を溜めてdequeue()で実行。3秒経ったらfadeOut()
        $("#timeout").fadeIn().queue(function() {
            setTimeout(function(){$("#timeout").dequeue();
            }, 3000);
        });
        $("#timeout").fadeOut();
});
} else {
/* ウィンドウサイズが 768px以上の場合のコードをここに */
//id属性値「text」のp要素を取得する

}




/* Jumpmenu
-------------------------------------------------------------------------------------------------------- */
function gotoURL(URL){
     if(URL!=""){
          window.location.href=URL;
     }
}




/* TOP slide
-------------------------------------------------------------------------------------------------------- */
  var mySwiper1 = new Swiper ('.main_img_slider .swiper-container1', {
    // ここからオプション
    //loop: true,
    loop: false, //現在停止中
    autoplay: {
        //delay: 4000,
		delay: 7000,
    },
    navigation: {
      nextEl: '.swiper-container1 .swiper-button-next',
      prevEl: '.swiper-container1 .swiper-button-prev',
    },
  })





/* TOP Information
-------------------------------------------------------------------------------------------------------- */  
if (window.matchMedia( "(max-width: 768px)" ).matches) {
/* ウィンドウサイズが 768px以下の場合のコードをここに */
  var mySwiper2 = new Swiper ('#information_area .swiper-container2', {
    // ここからオプション
    loop: true,
    slidesPerView: 2.2,
    navigation: {
        nextEl: '#information_area .swiper-button-next',
        prevEl: '#information_areas .swiper-button-prev',
    },
  })
} else {
/* ウィンドウサイズが 768px以上の場合のコードをここに */
  var mySwiper2 = new Swiper ('#information_area .swiper-container2', {
    // ここからオプション
    loop: true,
    slidesPerView: 4,
    navigation: {
        nextEl: '#information_area .swiper-button-next',
        prevEl: '#information_area .swiper-button-prev',
    },
  })
}





/* もっと見る
-------------------------------------------------------------------------------------------------------- */ 
function docOpen(argNo){
  var wArea = document.getElementById("area"+argNo);
  var wCheck= document.getElementById("ck"+argNo);
  var wDoc  = document.getElementById("doc"+argNo);
 
  if(wCheck.checked){
    wArea.style.height = parseInt(wDoc.clientHeight + 70)+"px";
  }else{
    wArea.style.height = "";
  }
}