/* Request runner to gather data from websites */
var siteRoot = 'https://www.readthis.cf';
var getData = function() {

var article_link = window.location.href.toString();

var article_title = document.title.toString();

var imgs = document.getElementsByTagName("img");
var imgSrcs = [];

for (var i = 0; i < imgs.length; i++) {
    imgSrcs.push(imgs[i].src);
}

var largest_dimension = 0;
var largest_image = 0;


for (var i = 0; i < imgSrcs.length; i++) {
	if ((imgSrcs[i].width * imgSrcs[i].height) > largest_dimension) {
		largest_image = i;
		largest_dimension = (imgSrcs[i].width * imgSrcs[i].height);
	}
}

var article_image = imgSrcs[largest_image].toString();

console.log(article_link)
console.log(article_title)
console.log(article_image)


$.ajax({
  type: "POST",
  contentType: "application/json; charset=utf-8",
  url: "https://www.readthis.cf/get-ajax-data",
  dataType: "json",
  data: JSON.stringify({'article_link': article_link,
  		 'article_title': article_title,
  		 'article_image': article_image}),
    success: function (data, textStatus, xhr) {
 	    console.log(data);
  	},
  	error: function (xhr, textStatus, errorThrown) {
   	 console.log('Error in Operation');
     console.log(data)
  	}
});}


function goBack() {
  window.history.back();
}

var RT_Div = document.createElement('div');
var Body = document.documentElement.outerHTML;
RT_Div.setAttribute('id','RT_Div');

var html = '<div class="icon-wrapper"><img class="icon" src="http://i64.tinypic.com/2u5uemr.jpg"></div><div class="content-wrapper"><form class="postre" method="POST"><a class="request" id="postreq" href="#">Like This?</a></form><a class="login" href="https://www.readthis.cf/">Login</a> to see what your friends thought of this!</div>';
RT_Div.innerHTML += html;

document.body.appendChild(RT_Div);

document.getElementById('postreq').onclick = getData;
