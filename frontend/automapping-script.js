window.onload = function() {
  setTimeout(function () {
      location.reload()
  }, 300000);
};

if ('serviceWorker' in navigator && 'caches' in window) {
  navigator.serviceWorker.register('./service-worker.min.js', {scope: './'} ).then(
      (reg) => {
        // registration worked
        console.log('Registration succeeded. Scope is ' + reg.scope);
        //// Clean expired tiles from the cache at startup
        reg.active.postMessage(JSON.stringify({action: 'PURGE_EXPIRED_TILES'}));
      }
  ).catch((error) => {
      console.log(`Registration failed with ${error}.`);
  });
}

apiUrl = "http://127.0.0.1:8000";

// ####################################
// # replaces content of specified DIV
// ####################################
function printToDivWithID(id,text){
  div = document.getElementById(id);
  div.innerHTML += text;
}

function cleanDivWithID(id){
  div = document.getElementById(id);
  div.innerHTML = "";
}

function OnClickLinkDetails(source_name, target_name, source_interfaces, target_interfaces ){
    cleanDivWithID("infobox")
    cleanDivWithID("infobox_header")

    printToDivWithID("infobox_header", source_name.id + " - " + target_name.id + "<br>")

    targetdiv = document.getElementById("infobox")

    fetch(apiUrl + "/stats/?devices=" + source_name.id + "&devices=" + target_name.id)
    .then(function(response) {
        if (response.status !== 200) {
          throw new Error('Looks like there was a problem. Status Code: ' + response.status);
        }
        return response.json();
    }).then(function(data){
          for (var iface of source_interfaces){

              var interface = data[source_name.id][iface];
              var iDivGraph = document.createElement('div');
              iDivGraph.id = source_name.id + "_" + interface['ifDescr'] + "_graph";
              targetdiv.appendChild(iDivGraph);

              draw_device_interface_graphs_to_div(interface,source_name.id, targetdiv)
          }
          for (var iface of target_interfaces){
              var interface = data[target_name.id][iface];
              var iDivGraph = document.createElement('div');
              iDivGraph.id = target_name.id + "_" + interface['ifDescr'] + "_graph";
              targetdiv.appendChild(iDivGraph);

              draw_device_interface_graphs_to_div(interface, target_name.id, targetdiv)
          }

    })
    .catch(function(err) {
      console.log('Fetch Error :-S', err);
    });
}

// ###################################
// # Graph Drawing Functions         #
// ###################################

// This draws a single specific interface to div
function draw_device_interface_graphs_to_div(interfaceName, deviceid, targetdiv){

        var iDiv = document.createElement('div');
        iDiv.id = deviceid + "_" + interfaceName['ifDescr'] + "_graph_header";
        iDiv.align = 'left';
        iDiv.innerHTML = "<br>" + deviceid + " - " + interfaceName['ifDescr'];
        targetdiv.appendChild(iDiv);

        var iDivGraph = document.createElement('div');
        iDivGraph.id = deviceid + "_" + interfaceName['ifDescr'] + "_graph";
        targetdiv.appendChild(iDivGraph);
        var TimeStampStrings = []
        var InOctetsData = []
        var OutOctetsData = []

        for (var stats of interfaceName['stats']){
            TimeStampStrings.push(stats['time'])
            InOctetsData.push(stats['InSpeed'])
            OutOctetsData.push(stats['OutSpeed'])
        }

        draw_graph_from_data_to_div(InOctetsData,OutOctetsData,TimeStampStrings,iDivGraph)
        //draw_graph_from_data_to_div_with_d3_with_brush(interfaceName['stats'], iDivGraph)

}

// This draws all interfaces from device to div
function draw_device_graphs_to_div(deviceid, data, targetdiv){

    for (var interface of data[deviceid]['interfaces']){
        draw_device_interface_graphs_to_div(interface,deviceid, targetdiv)
    }
}

function draw_graph_from_data_to_div_with_d3_with_brush(ifaceStats, iDivGraph){
  //var svg = d3.selectAll(iDivGraph)
  //    .append("svg")
  //    .attr("width", width)
  //    .attr("height", height)
  //var margin = {top: 20, right: 20, bottom: 170, left: 60},
  width = 460 // - margin.left - margin.right,
  height = 400 // - margin.top - margin.bottom;
  
  //var svg = d3.select(iDivGraph)
  //.append("svg")
  //.attr("width", width + margin.left + margin.right)
  //.attr("height", height + margin.top + margin.bottom)
  //.append("g")
  //.attr("transform",
  //      "translate(" + margin.left + "," + margin.top + ")");
  /*
  Brush & Zoom area chart block to work with mulit-line charts.
  Combining d3-brush and d3-zoom to implement Focus + Context.

  The focus chart is the main larger one where the zooming occurs.
  The context chart is the smaller one below where the brush is used to specify a focused area.
  */

  // sets margins for both charts
  var focusChartMargin = { top: 10, right: 20, bottom: 200, left: 20 };
  var contextChartMargin = { top: 180, right: 20, bottom: 10, left: 20 };

  // width of both charts
  var chartWidth = width - focusChartMargin.left - focusChartMargin.right;

  // height of either chart
  var focusChartHeight = height - focusChartMargin.top - focusChartMargin.bottom;
  var contextChartHeight = height - contextChartMargin.top - contextChartMargin.bottom;

  // bootstraps the d3 parent selection
  var svg = d3.select(iDivGraph)
    .append("svg")
    .attr("width", width)//chartWidth + focusChartMargin.left + focusChartMargin.right)
    .attr("height", height) //focusChartHeight + focusChartMargin.top + focusChartMargin.bottom)
    .append("g")
    //.attr("transform", "translate(" + focusChartMargin.left + "," + focusChartMargin.top + ")")
    //.attr("overflow", "visible");

  // function to parse date field
  //var parseTime = d3.timeParse("%H:%M");
  var parseTime = d3.timeParse("%y-%m-%d %I:%M:%S");

  // group all dates to get range for x axis later
  var dates = [];
  // group y axis values (value) of all lines to x axis (key)
  var groupValuesByX = {};
  //for (let key of Object.keys(data)) {
  var maxYAxisValue = -Infinity;
  for (let stats of ifaceStats) {
    //data[key].forEach(bucketRecord => {
      let parsedTime = parseTime(stats.time);

      dates.push(parsedTime);

      !(parsedTime in groupValuesByX) && (groupValuesByX[parsedTime] = {}); // if date as key does not exist then create
      groupValuesByX[parsedTime]['InSpeed'] = stats.InSpeed;
      groupValuesByX[parsedTime]['OutSpeed'] = stats.OutSpeed;
    //});
    let maxYAxisValuePerStat = Math.max(stats.InSpeed, stats.OutSpeed)
    maxYAxisValue = Math.max(maxYAxisValuePerStat, maxYAxisValue);
  }
  var availableDates = Object.keys(groupValuesByX);
  availableDates.sort(); // sort dates in increasing order
  console.log(groupValuesByX);
  console.log(availableDates);

  //get max Y axis value by searching for the highest conversion rate
  //var maxYAxisValue = -Infinity;
  //for (let key of Object.keys(data)) {
  //  let maxYAxisValuePerBucket = Math.ceil(d3.max(data[key], d => d["conversion"]));
  //  maxYAxisValue = Math.max(maxYAxisValuePerBucket, maxYAxisValue);
  //}

  // set the height of both y axis
  var yFocus = d3.scaleLinear().range([focusChartHeight, 0]);
  var yContext = d3.scaleLinear().range([contextChartHeight, 0]);

  // set the width of both x axis
  var xFocus = d3.scaleTime().range([0, chartWidth]);
  var xContext = d3.scaleTime().range([0, chartWidth]);

  // create both x axis to be rendered
  var xAxisFocus = d3
    .axisBottom(xFocus)
    .ticks(5)
    //.tickFormat(d3.timeFormat("%H:%M"));
    .tickFormat(d3.timeFormat("%y-%m-%d %I:%M:%S"));
  var xAxisContext = d3
    .axisBottom(xContext)
    .ticks(5)
    //.tickFormat(d3.timeFormat("%H:%M"));
    .tickFormat(d3.timeFormat("%y-%m-%d %I:%M:%S"));

  // create the one y axis to be rendered
  var yAxisFocus = d3.axisLeft(yFocus)//.tickFormat(d => d + "%");

  // build brush
  var brush = d3
    .brushX()
    .extent([
      [0, -10],
      [chartWidth, contextChartHeight]
    ])
    .on("brush end", brushed);

  // build zoom for the focus chart
  // as specified in "filter" - zooming in/out can be done by pinching on the trackpad while mouse is over focus chart
  // zooming in can also be done by double clicking while mouse is over focus chart
  var zoom = d3
    .zoom()
    .scaleExtent([1, Infinity])
    .translateExtent([
      [0, 0],
      [chartWidth, focusChartHeight]
    ])
    .extent([
      [0, 0],
      [chartWidth, focusChartHeight]
    ])
    .on("zoom", zoomed)
    .filter((event) => event.ctrlKey || event.type === "dblclick" || event.type === "mousedown");

  // create a line for focus chart
  var lineFocus = d3
    .line()
    //.x(d => xFocus(parseTime(d.date)))
    //.y(d => yFocus(d.conversion));
    .x(d => xFocus(parseTime(d.time)))
    .y(d => yFocus(d.InSpeed));
  // create a line for focus chart
  var lineFocusOut = d3
    .line()
    //.x(d => xFocus(parseTime(d.date)))
    //.y(d => yFocus(d.conversion));
    .x(d => xFocus(parseTime(d.time)))
    .y(d => yFocus(d.OutSpeed));

  // create line for context chart
  var lineContext = d3
    .line()
    //.x(d => xContext(parseTime(d.date)))
    //.y(d => yContext(d.conversion));
    .x(d => xContext(parseTime(d.time)))
    .y(d => yContext(d.InSpeed));

  // create line for context chart
  var lineContextOut = d3
    .line()
    //.x(d => xContext(parseTime(d.date)))
    //.y(d => yContext(d.conversion));
    .x(d => xContext(parseTime(d.time)))
    .y(d => yContext(d.OutSpeed));



  // es lint disabled here so react won't warn about not using variable "clip"
  /* eslint-disable */

  // clip is created so when the focus chart is zoomed in the data lines don't extend past the borders
  var clip = svg
    .append("defs")
    .append("svg:clipPath")
    .attr("id", "clip")
    .append("svg:rect")
    .attr("width", chartWidth)
    .attr("height", focusChartHeight)
    .attr("x", 0)
    .attr("y", 0);

  // append the clip
  var focusChartLines = svg
    .append("g")
    .attr("class", "focus")
    //.attr("transform", "translate(" + focusChartMargin.left + "," + focusChartMargin.top + ")")
    .attr("clip-path", "url(#clip)");

  /* eslint-enable */

  // create focus chart
  var focus = svg
    .append("g")
    .attr("class", "focus")
    //.attr("transform", "translate(" + focusChartMargin.left + "," + focusChartMargin.top + ")");

  // create context chart
  var context = svg
    .append("g")
    .attr("class", "context")
    .attr("transform", "translate(" + contextChartMargin.left + "," + (contextChartMargin.top + 50) + ")");

  // add data info to axis
  xFocus.domain(d3.extent(dates));
  yFocus.domain([0, maxYAxisValue]);
  xContext.domain(d3.extent(dates));
  yContext.domain(yFocus.domain());
  console.log(xContext);

  // add axis to focus chart
  focus
    .append("g")
    .attr("class", "x-axis")
    .attr("transform", "translate(0," + focusChartHeight + ")")
    .call(xAxisFocus);
  focus
    .append("g")
    .attr("class", "y-axis")
    .call(yAxisFocus);

  // get list of bucket names
  var bucketNames = ['InSpeed', 'OutSpeed'];
  //for (let key of Object.keys(data)) {
  //  bucketNames.push(key);
  //}

  // match colors to bucket name
  var colors = d3
    .scaleOrdinal()
    .domain(bucketNames)
    //.range(["#3498db", "#3cab4b", "#e74c3c", "#73169e", "#2ecc71"]);
    .range(["#3498db", "#2ecc71"]);

  // go through data and create/append lines to both charts
  //for (let key of Object.keys(data)) {
  //for (let bucket of ifaceStats) {
    //let bucket = data[key];
    focusChartLines
      .append("path")
      .datum(ifaceStats)
      .attr("class", "lineIn")
      .attr("fill", "none")
      //.attr("stroke", d => colors(key))
      //.attr("stroke-width", 1.5)
      .attr("d", lineFocus);

    context
      .append("path")
      .datum(ifaceStats)
      .attr("class", "lineIn")
      .attr("fill", "none")
      //.attr("stroke", d => colors(key))
      //.attr("stroke-width", 1.5)
      .attr("d", lineContext);

      focusChartLines
      .append("path")
      .datum(ifaceStats)
      .attr("class", "lineOut")
      .attr("fill", "none")
      //.attr("stroke", d => colors(key))
      .attr("stroke", "red")
      //.attr("stroke-width", 1.5)
      .attr("d", lineFocusOut);

      context
      .append("path")
      .datum(ifaceStats)
      .attr("class", "lineOut")
      .attr("fill", "none")
      //.attr("stroke", d => colors(key))
      .attr("stroke", "red")
      //.attr("stroke-width", 1.5)
      .attr("d", lineContextOut);
  //}

  // add x axis to context chart (y axis is not needed)
  context
    .append("g")
    .attr("class", "x-axis")
    .attr("transform", "translate(0," + contextChartHeight + ")")
    .call(xAxisContext);

  // add bush to context chart
  var contextBrush = context
    .append("g")
    .attr("class", "brush")
    .call(brush);

  // style brush resize handle
  var brushHandlePath = d => {
    var e = +(d.type === "e"),
      x = e ? 1 : -1,
      y = contextChartHeight + 10;
    return (
      "M" +
      0.5 * x +
      "," +
      y +
      "A6,6 0 0 " +
      e +
      " " +
      6.5 * x +
      "," +
      (y + 6) +
      "V" +
      (2 * y - 6) +
      "A6,6 0 0 " +
      e +
      " " +
      0.5 * x +
      "," +
      2 * y +
      "Z" +
      "M" +
      2.5 * x +
      "," +
      (y + 8) +
      "V" +
      (2 * y - 8) +
      "M" +
      4.5 * x +
      "," +
      (y + 8) +
      "V" +
      (2 * y - 8)
    );
  };

  var brushHandle = contextBrush
    .selectAll(".handle--custom")
    .data([{ type: "w" }, { type: "e" }])
    .enter()
    .append("path")
    .attr("class", "handle--custom")
    .attr("stroke", "#000")
    .attr("cursor", "ew-resize")
    .attr("d", brushHandlePath);

  // overlay the zoom area rectangle on top of the focus chart
  var rectOverlay = svg
    .append("rect")
    .attr("cursor", "move")
    .attr("fill", "none")
    .attr("pointer-events", "all")
    .attr("class", "zoom")
    .attr("width", chartWidth)
    .attr("height", focusChartHeight)
    //.attr("transform", "translate(" + focusChartMargin.left + "," + focusChartMargin.top + ")")
    .call(zoom)
    .on("mousemove", focusMouseMove)
    .on("mouseover", focusMouseOver)
    .on("mouseout", focusMouseOut);

  var mouseLine = focus
    .append("path") // create vertical line to follow mouse
    .attr("class", "mouse-line")
    .attr("stroke", "#303030")
    .attr("stroke-width", 2)
    .attr("opacity", "0");

  var tooltip = focus
    .append("g")
    .attr("class", "tooltip-wrapper")
    .attr("display", "none");

  var tooltipBackground = tooltip.append("rect").attr("fill", "#e8e8e8");

  var tooltipText = tooltip.append("text");

  contextBrush.call(brush.move, [0, chartWidth / 2]);

  // focus chart x label
  focus
    .append("text")
    //.attr("transform", "translate(" + chartWidth / 2 + " ," + (focusChartHeight + focusChartMargin.top + 25) + ")")
    .style("text-anchor", "middle")
    .style("font-size", "18px")
    .text("Time (UTC)");

  // focus chart y label
  focus
    .append("text")
    .attr("text-anchor", "middle")
    .attr("transform", "translate(" + (-focusChartMargin.left + 20) + "," + focusChartHeight / 2 + ")rotate(-90)")
    .style("font-size", "18px")
    .text("Conversion Rate");

  function brushed(event) {
    if (event.sourceEvent && event.sourceEvent.type === "zoom") return; // ignore brush-by-zoom
    tooltip.attr("display", "none");
    focus.selectAll(".tooltip-line-circles").remove();
    mouseLine.attr("opacity", "0");
    //var s = event.selection || xContext.range();
    //var s = xContext.range();
    var s = event.selection;
    //console.log(xContext, s);
    xFocus.domain(s.map(xContext.invert, xContext));
    focusChartLines.selectAll(".lineIn").attr("d", lineFocus);
    focusChartLines.selectAll(".lineOut").attr("d", lineFocusOut);
    focus.select(".x-axis").call(xAxisFocus);
    svg.select(".zoom").call(zoom.transform, d3.zoomIdentity.scale(chartWidth / (s[1] - s[0])).translate(-s[0], 0));
    brushHandle
      .attr("display", null)
      .attr("transform", (d, i) => "translate(" + [s[i], -contextChartHeight - 20] + ")");
  }

  function zoomed(event) {
    if (event.sourceEvent && event.sourceEvent.type === "brush") return; // ignore zoom-by-brush
    tooltip.attr("display", "none");
    focus.selectAll(".tooltip-line-circles").remove();
    mouseLine.attr("opacity", "0");
    var t = event.transform;
    xFocus.domain(t.rescaleX(xContext).domain());
    focusChartLines.selectAll(".lineIn").attr("d", lineFocus);
    focusChartLines.selectAll(".lineOut").attr("d", lineFocusOut);
    focus.select(".x-axis").call(xAxisFocus);
    var brushSelection = xFocus.range().map(t.invertX, t);
    context.select(".brush").call(brush.move, brushSelection);
    brushHandle
      .attr("display", null)
      .attr("transform", (d, i) => "translate(" + [brushSelection[i], -contextChartHeight - 20] + ")");
  }

  //function focusMouseMove() {
  function focusMouseMove(event) {
    tooltip.attr("display", null);
    //var mouse = d3.mouse(this);
    var mouse = d3.pointer(event);
    var dateOnMouse = xFocus.invert(mouse[0]);
    var nearestDateIndex = d3.bisect(availableDates, dateOnMouse.toString());
    // get the dates on either of the mouse cord
    var d0 = new Date(availableDates[nearestDateIndex - 1]);
    var d1 = new Date(availableDates[nearestDateIndex]);
    var closestDate;
    if (d0 < xFocus.domain()[0]) {
      closestDate = d1;
    } else if (d1 > xFocus.domain()[1]) {
      closestDate = d0;
    } else {
      // decide which date is closest to the mouse
      closestDate = dateOnMouse - d0 > d1 - dateOnMouse ? d1 : d0;
    }

    var nearestDateYValues = groupValuesByX[closestDate];
    var nearestDateXCord = xFocus(new Date(closestDate));

    mouseLine.attr("d", `M ${nearestDateXCord} 0 V ${focusChartHeight}`).attr("opacity", "1");

    tooltipText.selectAll(".tooltip-text-line").remove();
    focus.selectAll(".tooltip-line-circles").remove();
    console.log(xFocus.domain());
    var formatTime = d3.timeFormat("%y-%m-%d %I:%M:%S");
    //var formatTime = d3.timeFormat("%H:%M"); 
    tooltipText
      .append("tspan")
      .attr("class", "tooltip-text-line")
      .attr("x", "5")
      .attr("y", "5")
      .attr("dy", "13px")
      .attr("font-weight", "bold")
      .text(`${formatTime(closestDate)}`);

    for (let key of Object.keys(nearestDateYValues)) {
      focus
        .append("circle")
        .attr("class", "tooltip-line-circles")
        .attr("r", 5)
        .attr("fill", colors(key))
        .attr("cx", nearestDateXCord)
        .attr("cy", yFocus(nearestDateYValues[key]));

      tooltipText
        .append("tspan")
        .attr("class", "tooltip-text-line")
        .attr("x", "5")
        .attr("dy", `14px`)
        .attr("fill", colors(key))
        .text(`${key}: ${nearestDateYValues[key].toFixed(2)}`);
    }

    var tooltipWidth = tooltipText.node().getBBox().width;
    var tooltipHeight = tooltipText.node().getBBox().height;
    var rectOverlayWidth = rectOverlay.node().getBBox().width;
    tooltipBackground.attr("width", tooltipWidth + 10).attr("height", tooltipHeight + 10);
    if (nearestDateXCord + tooltipWidth >= rectOverlayWidth) {
      tooltip.attr("transform", "translate(" + (nearestDateXCord - tooltipWidth - 20) + "," + mouse[1] + ")");
    } else {
      tooltip.attr("transform", "translate(" + (nearestDateXCord + 10) + "," + mouse[1] + ")");
    }
  }

  function focusMouseOver() {
    mouseLine.attr("opacity", "1");
    tooltip.attr("display", null);
  }

  function focusMouseOut() {
    mouseLine.attr("opacity", "0");
    tooltip.attr("display", "none");
    focus.selectAll(".tooltip-line-circles").remove();
  }
  
  return svg.node()

}



function draw_graph_from_data_to_div_with_d3(ifaceStats, iDivGraph){

    // Trying to replace Plotly by pure d3

    var parseTime = d3.timeParse("%y-%m-%d %I:%M:%S");

    // set the dimensions and margins of the graph
    var margin = {top: 20, right: 20, bottom: 170, left: 60},
    width = 460 - margin.left - margin.right,
    height = 400 - margin.top - margin.bottom;

    // set the dimensions and margins of the graph
    var marginBrush = {top: 260, right: 30, bottom: 90, left: 60},
    heightBrush = 400 - marginBrush.top - marginBrush.bottom;

    // set the ranges
    var x = d3.scaleTime().range([0, width]);
    var y = d3.scaleLinear().range([height, 0]);
    
    // define the 1st line
    var valueline = d3.line()
        .x(function(d) { return x(parseTime(d.time)); })
        .y(function(d) { return y(d.InSpeed); });
    
    // define the 2nd line
    var valueline2 = d3.line()
        .x(function(d) { return x(parseTime(d.time)); })
        .y(function(d) { return y(d.OutSpeed); });

    // append the svg object to the body of the page
    var svg = d3.select(iDivGraph)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform",
          "translate(" + margin.left + "," + margin.top + ")");
    
    // Scale the range of the data
    x.domain(d3.extent(ifaceStats, function(d) { return parseTime(d.time); }));
    y.domain([0, d3.max(ifaceStats, function(d) {
      return Math.max(d.InSpeed, d.OutSpeed);
    })]);

    // Add the valueline path.
    svg.append("path")
        .data([ifaceStats])
        .attr("class", "line")
        .attr("d", valueline);

    // Add the valueline2 path.
    svg.append("path")
        .data([ifaceStats])
        .attr("class", "line")
        .style("stroke", "red")
        .attr("d", valueline2);

    // Add the X Axis
    svg.append("g")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x));

    // Add the Y Axis
    svg.append("g")
        .call(d3.axisLeft(y));
}

function draw_graph_from_data_to_div(InOctetsData,OutOctetsData,TimeStampStrings,iDivGraph){

    var selectorOptions = {
      buttons: [
      {
          step: 'day',
          stepmode: 'todate',
          count: 1,
          label: '1d'
      }, {
          step: 'day',
          stepmode: 'todate',
          count: 3,
          label: '3d'
      }, {
          step: 'day',
          stepmode: 'todate',
          count: 7,
          label: '1w'
      }, {
          step: 'month',
          stepmode: 'todate',
          count: 1,
          label: '1m'
      }, {
          step: 'month',
          stepmode: 'todate',
          count: 3,
          label: '3m'
      }, {
          step: 'month',
          stepmode: 'todate',
          count: 6,
          label: '6m'
      }, {
          step: 'year',
          stepmode: 'todate',
          count: 1,
          label: '1y'
      }, {
          step: 'all',
      }],
    };

    traceOut = {
      type: 'scatter',
      x: TimeStampStrings,
      y: OutOctetsData,
      mode: 'lines',
      name: 'Out',
      line: {
        color: 'rgb(219, 64, 82)',
        width: 3
      }
    };

    traceIn = {
      type: 'scatter',
      x: TimeStampStrings,
      y: InOctetsData,
      mode: 'lines',
      name: 'In',
      line: {
        color: 'rgb(55, 128, 191)',
        width: 3
      }
    };

    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    var layout = {
      color: '#fff',
      margin: {
        //autoexpand: true,
        l: 35,
        r: 20,
        t: 5,
        b: 35
      },
      width: 600,
      height: 350,
      xaxis: {
        title: 'Time',
        //showgrid: true,
        zeroline: true,
        showline: true,
        //linecolor: '#fff',
        rangeselector: selectorOptions,
        rangeslider: {},
        autorange: false,
        range: [yesterday, today],
        type: "date"
      },
      yaxis: {
        title: 'bps',
        showline: true,
        //linecolor: '#fff',
        showtickprefix: 'first'
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)'
    };

    var data = [traceOut, traceIn];

    var config = {
      toImageButtonOptions: {
        format: 'svg', // one of png, svg, jpeg, webp
        filename: 'traffic',
        height: 250,
        width: 600,
        scale: 1 // Multiply title/legend/axis/canvas sizes by this factor
      },
      modeBarButtonsToRemove:['sendDataTocloud', 'zoomIn2d', 'zoomOut2d','autoScale2d','resetScale2d','resetViewMapBox','resetViews'],
      displaylogo: false,
      responsive: true
    };

    //Plotly.newPlot(iDivGraph, data, layout, {showSendToCloud: false});
    console.time('Draw_device_iface')
    Plotly.react(iDivGraph, data, layout, config);

    console.timeEnd('Draw_device_iface')
}


// =============================
// PRINTING DEVICE DETAILS TABLE
// =============================

function viewChangeFunc(deviceid) {
    var selectBox = document.getElementById("viewSelectBox");
    var selectedValue = selectBox.options[selectBox.selectedIndex].value;
    OnViewChange(deviceid,selectedValue);
}

function OnClickDetails(deviceid, view = "neighbors"){
    cleanDivWithID("infobox_header")
    printToDivWithID("infobox_header",deviceid);
    view_select_box = ""
    view_select_box += "<div>views: <select id=\"viewSelectBox\" onchange=\"viewChangeFunc(\'"+deviceid+"\');\">"
    view_select_box += "<option value=\"neighbors\">Neighbors</option>"
    view_select_box += "<option value=\"traffic\">Traffic</option>"
    view_select_box += "<option value=\"clear\">Clear</option>"
    view_select_box += "</select></div><br>"
    printToDivWithID("infobox_header",view_select_box)

    // ## INITIATE FIRST PASSIVE VIEW CHANGE
    OnViewChange(deviceid)
}

function OnViewChange(deviceid, view = "neighbors"){
    // # Initial cleanup
    cleanDivWithID("infobox")

    // #############################
    // # CREATING GRAPHS      #
    // #############################
    if (view == "traffic"){
        fetch(apiUrl + "/stats/?devices=" + deviceid)
        .then(
          function(response) {
            if (response.status !== 200) {
              console.log('Looks like there was a problem. Status Code: ' +
                response.status);
              return;
            }
            response.json().then(function(data) {

              for (var iface in data[deviceid]) {
                var interface = data[deviceid][iface]
                var targetdiv = document.getElementById("infobox")
                var iDivGraph = document.createElement('div');
                iDivGraph.id = deviceid + "_" + interface['ifDescr'] + "_graph";
                targetdiv.appendChild(iDivGraph);
                draw_device_interface_graphs_to_div(interface, deviceid, iDivGraph)
              }
            });
          }
        )
        .catch(function(err) {
          console.log('Fetch Error :-S', err);
        });
    }
    // #############################
    // # READING NEIGHBORS VIEW    #
    // #############################
    else if (view == "neighbors"){
        fetch(apiUrl + "/neighborships/?device=" + deviceid)
        .then(
          function(response) {
            if (response.status !== 200) {
              console.log('Looks like there was a problem. Status Code: ' +
                response.status);
              return;
            }
            response.json().then(function(data) {
              if (data.length !== 0) { 
                  printToDivWithID("infobox",tableFromNeighbor(data));
              }
              else {
                warning_text = "<h4>The selected device id: ";
                warning_text+= deviceid;
                warning_text+= " is not in database!</h4>";
                warning_text+= "This is most probably as you clicked on edge node ";
                warning_text+= "that is not SNMP data gathered, try clicking on its neighbors.";
                printToDivWithID("infobox",warning_text);
              }
            });
          }
        )
        .catch(function(err) {
          console.log('Fetch Error :-S', err);
        });
    } else if (view == "clear"){
      cleanDivWithID("infobox");
      //cleanDivWithID("infobox_header")
    };
}

// ####################################
// # using input parameters returns
// # HTML table with these inputs
// ####################################
function tableFromUnusedInterfaces(key,data){
  text = "<table class=\"infobox2\">";
  text+= "<thead><th>LOCAL INT.</th><th>TYPE</th><th>SPEED</th>";
  text+= "</thead>";

  for (var neighbor in data[key]) {
    text+= "<tr>";

    //console.log("local_intf:" + data[key][neighbor]['ifDescr']);
    text+= "<td>" + data[key][neighbor]['ifDescr'] + "</td>";
    //console.log("description:" + data[key][neighbor]['ifType']);
    text+= "<td>" + data[key][neighbor]['ifType'] + "</td>";
    //console.log("actual_bandwith:" + data[key][neighbor]['ifSpeed']);
    text+= "<td>" + data[key][neighbor]['ifSpeed'] + "</td>";

    text+= "</tr>";
  }

  text+= "</table>";

  return text;
}

// ####################################
// # using input parameters returns
// # HTML table with these inputs
// ####################################
function tableFromNeighbor(data){
  text = "<table class=\"infobox\">";
  text+= "<thead><th>LOCAL INT.</th><th>NEIGHBOR</th><th>NEIGHBOR'S INT</th>";
  text+= "</thead>";

  for (let neighbor of data) {
    text+= "<tr>";

    //console.log("local_intf:" + neighbor['local_intf']);
    text+= "<td>" + neighbor['local_intf'] + "</td>";
    //console.log("neighbor_intf:" + neighbor['neighbor_intf']);
    text+= "<td>" + neighbor['neighbor'] + "</td>";
    //console.log("neighbor:" + neighbor['neighbor']);
    text+= "<td>" + neighbor['neighbor_intf'] + "</td>";

    text+= "</tr>";
  }

  text+= "</table>";

  return text;
}

// #######################################
// ########### NAV BUTTONS ###############
// #######################################
document.getElementById("down-button").addEventListener("mousedown", navDownFunctionClick);
document.getElementById("down-button").addEventListener("mouseup", navRelease);
document.getElementById("up-button").addEventListener("mousedown", navUpFunctionClick);
document.getElementById("up-button").addEventListener("mouseup", navRelease);
document.getElementById("left-button").addEventListener("mousedown", navLeftFunctionClick);
document.getElementById("left-button").addEventListener("mouseup", navRelease);
document.getElementById("right-button").addEventListener("mousedown", navRightFunctionClick);
document.getElementById("right-button").addEventListener("mouseup", navRelease);

document.addEventListener("mouseup", navRelease);
document.addEventListener("mouseout", navRelease);

// ########### VARIABLES #################
var MouseDownID = -1;
var x_trans = 0
var y_trans = 0

// ########### TRANSFORM FUNCTION ########
// Change element attribute
function transform_delta(delta_x,delta_y){
	var nodes_g = document.getElementById('nodes-g');
	var links_g = document.getElementById('links-g');
	//console.log("Current transforms: " + x_trans + ":" + y_trans)
	x_trans = x_trans + delta_x
	y_trans = y_trans + delta_y
	//console.log("New transforms: " + x_trans + ":" + y_trans)
	nodes_g.setAttribute("transform", "translate(" + x_trans + "," + y_trans +")")
	links_g.setAttribute("transform", "translate(" + x_trans + "," + y_trans +")")
}

// ########### DOWN BUTTON ###############
function navDownFunctionClick() {
  document.getElementById("down-button").style["color"] = "red";
  //console.log("navDownFunctionClick")
  if(MouseDownID==-1)  //Prevent multimple loops!
     MouseDownID = setInterval(WhileNavDownMouseDown, 100 /*execute every 100ms*/);
}
function WhileNavDownMouseDown() {
   //console.log("WhileNavDownMouseDown")
   transform_delta(0,10)
}

// ########### UP BUTTON ###############
function navUpFunctionClick() {
  document.getElementById("up-button").style["color"] = "red";
  //console.log("navUpFunctionClick")
  if(MouseDownID==-1)  //Prevent multimple loops!
     MouseDownID = setInterval(WhileNavUpMouseDown, 100 /*execute every 100ms*/);
}
function WhileNavUpMouseDown() {
   //console.log("WhileNavUpMouseDown")
   transform_delta(0,-10)
}
// ########### LEFT BUTTON ###############
function navLeftFunctionClick() {
  document.getElementById("left-button").style["color"] = "red";
  //console.log("navLeftFunctionClick")
  if(MouseDownID==-1)  //Prevent multimple loops!
     MouseDownID = setInterval(WhileNavLeftMouseDown, 100 /*execute every 100ms*/);
}
function WhileNavLeftMouseDown() {
   //console.log("WhileNavLeftMouseDown")
   transform_delta(-10,0)
}

// ########### RIGHT BUTTON ###############
function navRightFunctionClick() {
  document.getElementById("right-button").style["color"] = "red";
  //console.log("navRightFunctionClick")
  if(MouseDownID==-1)  //Prevent multimple loops!
     MouseDownID = setInterval(WhileNavRightMouseDown, 100 /*execute every 100ms*/);
}
function WhileNavRightMouseDown() {
   //console.log("WhileNavRightMouseDown")
   transform_delta(10,0)
}


// ########### COMMON RELEASE BUTTON ###############
function navRelease() {
  //console.log("navRelease")
  document.getElementById("down-button").style["color"] = "black";
  document.getElementById("up-button").style["color"] = "black";
  document.getElementById("left-button").style["color"] = "black";
  document.getElementById("right-button").style["color"] = "black";
  clearInterval(MouseDownID)
  MouseDownID = -1;
}

// ###########################
// RESIZE SVG ON WINDOW RESIZE
// ###########################

var intervalID = setInterval(resize_svg_on_window_resize, 5000);
function resize_svg_on_window_resize(){
    //console.log("resize_svg_on_window_resize TRIGGERED")
    var svg_element = document.getElementById('primary-svg');
    var original_viewBox = svg_element.getAttribute("viewBox")
    var res = original_viewBox.split(" ");

    // ### SELECT EITHER LEFT SIDEBAR OR WINDOW AS THE NEW HIGHT WHICHEVER IS BIGGER
    windowHeight = window.innerHeight; //|| document.documentElement.clientHeight || document.body.clientHeight;
    var rect = document.getElementById('left-sidebar').getBoundingClientRect();

    if (rect.height > windowHeight){
        var newClientHeight = rect.height;
    } else {
        var newClientHeight = windowHeight;
    }

    // ### SET THE HIGHT OF THE SVG AND SURROUNDING CONTAINER
    //console.log("new height: " + newClientHeight)
    svg_element.setAttribute("viewBox", res[0] + " " + res[1] + " " + res[2] + " " + newClientHeight)
    // Trying to set height of main SVG
    document.getElementById('container').style.height = newClientHeight + "px";

    //slider_input()
}


// ########
// # MAIN #
// ########

// #################################
var svg = d3.select("div#container")
    .append("svg")
    .attr("id", "primary-svg")
    .attr("preserveAspectRatio", "xMinYMin")
    .attr("viewBox", "0 0 800 600")
    //.attr("viewBox", [0, 0, width, height])
    .classed("svg-content", true);



var svg_element = document.getElementById('primary-svg');
var positionInfo = svg_element.getBoundingClientRect();
    height = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
    //console.log(window.innerHeight, document.documentElement.clientHeight, document.body.clientHeight);
    //height =  2160;
    width = positionInfo.width ;
    //width = 3840;
    svg_element.setAttribute("preserveAspectRatio", "xMinYMin")
    svg_element.setAttribute("viewBox", "0 0 " + width + " " + height)
    //console.log("Initial width:" + width)
    //console.log("Initial height:"+ height)

// Trying to set height of main SVG
document.getElementById('container').style.height = height + "px";

// ###########  Scale Slider controls ##########
//var slider = document.getElementById("scale_slider");
//var output = document.getElementById("scale_indicator");
//output.value = width
//output.innerHTML = width;
//initial_scale = width
//
//slider.addEventListener("input", slider_input);
//
//function slider_input() {
//  var slider = document.getElementById("scale_slider");
//
//  output.innerHTML = slider.value;
//  //console.log("Scale_input: " + slider.value)
//
//  // Change element attribute
//  var svg_element = document.getElementById('primary-svg');
//  var original_viewBox = svg_element.getAttribute("viewBox")
//  var res = original_viewBox.split(" ");
//  res[0] = (initial_scale - slider.value) / 2
//  wh_ratio = ( (window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight) / initial_scale )
//  res[1] = wh_ratio + res[0] * wh_ratio
//  //console.log("view X: " + res[0] + " view Y: " + res[1])
//  svg_element.setAttribute("viewBox", res[0] + " " + res[1] + " " + slider.value + " " + slider.value)
//}

// ###########  FORCE Slider controls ##########
var force_slider = document.getElementById("force_slider");
var force_output = document.getElementById("force_indicator");
force_output.value = 100
//console.log("Force_output.value:" + force_output.value)
force_output.innerHTML = force_output.value;

force_slider.oninput = function() {
  force_output.innerHTML = this.value;
  //console.log("force_output: " + this.value)

  //simulation.force("y", d3.forceY(height/2).strength(this.value / 1000))  //### PARAMETRIZED FORCE TO SLIDER
  simulation.force("y", d3.forceY(function(d){ return (d.groupy * height * 0.1 / 6)}).strength(this.value / 1000))  //### PARAMETRIZED FORCE TO SLIDER
  //console.log("starting simulation");
  simulation.alphaTarget(0.03).restart()
  simulation.alpha(1).restart()
  //delay
  setTimeout(function(){ simulation.alphaTarget(0); /*console.log("Ending simulation");*/ }, "1000")
}

// ##### GRAPH POPULATION #######
var color = d3.scaleOrdinal(d3.schemeCategory10);

var simulation = d3.forceSimulation()
    .force("link", d3.forceLink().id(function(d) { return d.id }).distance(100).strength(0.001))
    .force("charge", d3.forceManyBody().strength(-200).distanceMax(500).distanceMin(150))
    .force("x", d3.forceX(function(d){ return (d.groupx * width * 0.7 / 6)}).strength(1))
    .force("y", d3.forceY(function(d){ return (d.groupy * height * 0.1 / 6)}).strength(force_output.value / 1000))  //### PARAMETRIZED FORCE TO SLIDER
    .force("center", d3.forceCenter(width * 2/3, height / 2))
    .force("collision", d3.forceCollide().radius(25));
    //.force("y", d3.forceY(height/2).strength(force_output.value / 1000))  //### PARAMETRIZED FORCE TO SLIDER

// #########################################
// # Get graph from api and draw SVG graph #
// #########################################
function percentage_to_utilization_color(percentage){
    if (percentage >= 90.0){
        return "#ff0e06"
    } else if (percentage >= 75.0){
        return "#ff6906"
    } else if (percentage >= 50.0){
        return "#f9e320"
    } else if (percentage >= 35.0){
        return "#00ce30"
    } else if (percentage >= 25.0){
        return "#5cd2c3"
    } else if (percentage >= 10.0){
        return "#001693"
    } else if (percentage > 0.0){
        return "#ffffff"
    } else {
        return "#646464"
    }
}

//console.time('getGraph')
d3.json(apiUrl + "/graph")
  .then(function(graph) {

    //console.timeEnd('getGraph')
    //console.time('createLinksGraph')

    links = graph.links

    var link = svg.append("g")
      .attr("id","links-g")
      .selectAll("path")
      .data(links)
      .enter()
        .append("a")
        .attr("target", '_blank')
        .attr("xlink:href", function(d) { /*console.log(d);*/ return (window.location.href + '?node_a=' + d.source + "&node_b=" + d.target) })
        .append("path")
        .attr("fill", "none")
        //.attr("opacity", "0%")
        .attr("stroke", function(d) { return percentage_to_utilization_color(d.highest_utilization) })   // # COLOR
        .attr("stroke-width", function(d) { return (Math.sqrt(parseInt(d.speed) / 1000000)) % 10 })  // # WIDTH
        .attr("source", function(d) { d.source })
        .attr("target", function(d) { d.target }
    );

    //console.timeEnd('createLinksGraph')

    //console.time('AddLinksEventGraph')
    link.on("click", function(event, d){
      //d3.event.preventDefault();
      //d3.event.stopPropagation();
      event.preventDefault();
      event.stopPropagation();
      OnClickLinkDetails(d.source,d.target,d.source_interfaces,d.target_interfaces);
      resize_svg_on_window_resize()
    });
    //console.timeEnd('AddLinksEventGraph')

    //console.time('AddNodesGraph')
    var node = svg.append("g")
      .attr("class", "nodes")
      .attr("id","nodes-g")
      .attr("cursor", "grab")
      .selectAll("a")
      .data(graph.nodes)
      .enter().append("a")
        .attr("target", '_blank')
        .attr("xlink:href",  function(d) { return (window.location.href + '?device=' + d.id)
    });
    //console.timeEnd('AddNodesGraph')

    //console.time('AddNodesEventGraph')
    node.on("click", function(event, d){
      event.preventDefault();
      event.stopPropagation();
      OnClickDetails(d.id);
      resize_svg_on_window_resize()
    });


    node.call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended)
    );
    //console.timeEnd('AddNodesEventGraph')

    //console.time('AddEventGraph')
    svg.call(d3.zoom()
      .extent([[0, 0], [width, height]])
      .scaleExtent([1, 8])
      .on("zoom", zoomed)
    );
    //var drag = force.drag()
    svg.call(d3.drag()
    .on("start", onDragStart)
    .on("drag", onDrag));

    //console.timeEnd('AddEventGraph')

    //console.time('AddNodeImageGraph')
    node.append("image")
      .attr("xlink:href", function(d) { return ("img/" + d.image); })
      .attr("width", 32)
      .attr("height", 32)
      .attr("x", - 16)
      .attr("y", - 16)
      .attr("fill", function(d) { /*console.log(d.group) ; */ return color(d.groupx)
    });
    //console.timeEnd('AddNodeImageGraph')

    //console.time('AddNodeTextGraph')
    node.append("text")
      .attr("font-size", "1em")
      .style("fill", "#ffffff")
      .attr("dx", 12)
      .attr("dy", ".35em")
      .attr("x", +8)
      .text(function(d) { return d.id }
    );

    node.append("title")
      .text(function(d) { return d.id; }
    );

    //console.timeEnd('AddNodeTextGraph')

    //console.time('startSimulationGraph')
    simulation
      .nodes(graph.nodes)
      .on("tick", ticked);

    simulation.force("link")
      .links(links);

    //console.timeEnd('startSimulationGraph')

    function ticked() {
      link
        .attr("d", function(d) {
          //if (d.linknum === 1) {            
            //link
            //  .attr("x1", function(d) { return d.source.x; })
            //  .attr("y1", function(d) { return d.source.y; })
            //  .attr("x2", function(d) { return d.target.x; })
            //  .attr("y2", function(d) { return d.target.y; });
            return "M" + d.source.x + "," + d.source.y + "L" + d.target.x + "," + d.target.y;
          //} else {
          //  // Not used anymore for clarity
          //  // Should come in the future in a better form : 
          //  //     by clicking on an aggregated link, it disaggregate into multiple links (doable 
          //  //     with d3 but pretty complex)
          //  let dx = d.target.x - d.source.x,
          //    dy = d.target.y - d.source.y,
          //    t = Math.sqrt(dx * dx + dy * dy),
          //    //half_n = Math.floor(links.length / 2) + links.length % 2,
          //    half_n = Math.floor(d.source_interfaces.length / 2) + d.source_interfaces.length % 2,
          //    //dr = d.linknum == half_n ? t * 100 : 2.25 * t * (half_n - Math.abs(d.linknum - half_n)) / d.source_interfaces.length,
          //    drx = d.linknum <= half_n ? d.linknum * (t / d.source_interfaces.length) : (d.linknum + 1 - half_n) * (t / (d.source_interfaces.length)),
          //    dry = d.linknum <= half_n ? d.linknum * (t / d.source_interfaces.length) : (d.linknum + 1 - half_n) * (t / (d.source_interfaces.length)),
          //    //dr = d.linknum == half_n ? t * 100 : 10.25 * t * (half_n - Math.abs(d.linknum - half_n)) / links.length,
          //    sweep = d.linknum <= half_n ? 1 : 0;
          //    //console.log(d.linknum, half_n, drx, dry, sweep);
          //  return "M" + d.source.x + "," + d.source.y + "A" + drx + "," + dry + " 0 0," + sweep + " " + d.target.x + "," + d.target.y;
          //}
      });

      node
        .attr("transform", function(d) { return "translate(" + d.x + "," + Math.min(Math.max(20, d.y), height - 20) + ")"});
    }
})
.catch(function(error){
  throw error;
});


function dragstarted(event, d) {
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}

function dragended(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

function validate(x, a, b) {
    if (x < a) x = a;
    if (x > b) x = b;
    return x;
}

function onDragStart(d) {
    d.fixed = true;
}

function onDrag(d) {
   d.px = validate(d.px, 0, w);
   d.py = validate(d.py, 0, h);
}


function zoomed(event) {
  svg.attr("transform", event.transform);
}

// ### LAST IN SCRIPT UPDATING SLIDER POSITION
// ###########################################
//var elem = document.getElementById("scale_slider");
//var svg_element = document.getElementById('primary-svg');
//var positionInfo = svg_element.getBoundingClientRect();
//elem.value = positionInfo.width;
//var elem2 = document.getElementById("scale_indicator");
//elem2.value = positionInfo.width;
