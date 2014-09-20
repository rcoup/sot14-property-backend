var win = window,
    doc = document,
    eey = doc.documentElement,
    gee = doc.getElementsByTagName('body')[0],
    xx = win.innerWidth || eey.clientWidth || gee.clientWidth,
    yy = win.innerHeight|| eey.clientHeight|| gee.clientHeight;

var margin = {top: 10, right: 25, bottom: 100, left: 25},
    margin2 = {top: 10, right: 25, bottom: 30, left: 25},
    width = xx - margin.left - margin.right,
    height = 80 - margin.top - margin.bottom,
    height2 = 80 - margin2.top - margin2.bottom;

var parseDate = d3.time.format("%b %Y").parse;

var x = d3.time.scale().range([0, width]),
    x2 = d3.time.scale().range([0, width]),
    y = d3.scale.linear().range([height, 0]),
    y2 = d3.scale.linear().range([height2, 0]);

var xAxis = d3.svg.axis().scale(x).orient("bottom"),
    xAxis2 = d3.svg.axis().scale(x2).orient("bottom"),
    yAxis = d3.svg.axis().scale(y).orient("left");

var brush = d3.svg.brush()
    .x(x2)
    .on("brush", brushed);

var area = d3.svg.area()
    .interpolate("monotone")
    .x(function(d) { return x(d.date); })
    .y0(height)
    .y1(function(d) { return y(d.price); });

var area2 = d3.svg.area()
    .interpolate("monotone")
    .x(function(d) { return x2(d.date); })
    .y0(height2)
    .y1(function(d) { return y2(d.price); });

var svg = d3.select('#brush').append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);

svg.append("defs").append("clipPath")
    .attr("id", "clip")
  .append("rect")
    .attr("width", width)
    .attr("height", height);

var context = svg.append("g")
    .attr("class", "context")
    .attr("transform", "translate(" + margin2.left + "," + margin2.top + ")");
// http://localhost:5000/week/2013-08-03
// d3.json("../../../assets/json/tweetTags.json", function(error, json) {

d3.csv("sp500.csv", type, function(error, data) {
  x.domain(d3.extent(data.map(function(d) { return d.date; })));
  y.domain([0, d3.max(data.map(function(d) { return d.price; }))]);
  x2.domain(x.domain());
  y2.domain(y.domain());

  context.append("path")
      .datum(data)
      .attr("class", "area")
      .attr("d", area2);

  context.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height2 + ")")
      .call(xAxis2);

  context.append("g")
      .attr("class", "x brush")
      .call(brush)
    .selectAll("rect")
      .attr("y", -6)
      .attr("height", height2 + 7);
});

function brushed() {
  x.domain(brush.empty() ? x2.domain() : brush.extent());
  console.log(x.domain())
}

function type(d) {
  d.date = parseDate(d.date);
  d.price = +d.price;
  return d;
}