var returnedItemsAgingComplete; //items from query of complete aging SP list
var returnedItemsAgingLog; //items from query of aging error log SP list
var PartNumbers; //array of Part numbers to be displayed in the tables/graphs. Ignored if the Dimm Die type has been changed since Dimms wouldn't be valid anymore
var radioCount; //count for number of radio elements
var DimmDie; //name of current dimm die type
var tagsPrevious = false; //tags previous keeps track of whether radio buttons have already been made or not
var datesFailedDimmArr = []; //array of dates of failed dimms
var dimmDict = {}; //object structured as dimm name -> date -> total dimm count
var tableDict = {}; //object structured as customer name -> date -> dimm name -> total dimm count
var backgroundColorDonut = []; //array of background colors for Donut chart/table
var sumTotal = 0; //sum of all dimms
var avgTTF = 0; //average TTF time
var ppmArrAvg = 0; //average ppm failure rate
var oldDimmDie; //name of last Dimm Die type chosen
var customerTotalDimmArr = []; //array of customer names with associated dimm counts
const urlSP = "http://sharepoint.ssi.samsung.com/biz/CQMP/"; //sharepoint url
const dropdowns = getDropdowns(2); //dropdown objects


/**
 * listImport executes a CAML query to grab all entries of one of our completed aging generation pages.
 * 
 * @param DimmDieTemp string containing name of DIMM die to query for
 * @param PartNumbersTemp array of strings of part number names we want to sort for
 * 
 * @returns Executes the query asynchronously. If successful, execute AgingErrorLogImport function. If unsuccessful, execute failed function.
*/
function listImport(DimmDieTemp, PartNumbersTemp) {
  //initialize defaults in case data is not available from tables later on.
  returnedItemsAgingComplete = null;
  radioCount = 0;
  PartNumbers = PartNumbersTemp;
  DimmDie = DimmDieTemp;
  datesFailedDimmArr = [];
  dimmDict = {};
  tableDict = {};
  backgroundColorDonut = [];
  sumTotal = 0;
  avgTTF = 0;
  ppmArrAvg = 0;
  customerTotalDimmArr = [];

  //get a sharepoint client context object of our webpage, then get the list we want from it
  var ctx = new SP.ClientContext(urlSP);
  var listName = "Completed Aging " + DimmDie;
  var oList = ctx.get_web().get_lists().getByTitle(listName);

  //create CAML Query to grab all items from our list
  var caml = new SP.CamlQuery();
  caml.set_viewXml("<View><RowLimit>0</RowLimit></View>");
  returnedItemsAgingComplete = oList.getItems(caml);

  //load the context and execute the query
  ctx.load(returnedItemsAgingComplete);
  return ctx.executeQueryAsync(AgingErrorLogImport, failed);
}

/**
 * updatePage executes only if we have successfully executed our queries for the aging Error Log
 * and completed aging sharepoint lists.
 * 
 * updatePage calls other functions to update the HTML for the following:
 * -  all dropdowns 
 * -  all graphs
 * -  all tables
 */
function updatePage() {
  updateTableNames();
  getDataFromSPList();
  updateProductHistoryTable();
  updateLineChart();
  updateDonutChartTable();
  updateSelectedPartsInfoTable();
  tagsPrevious = true;
  sortproductHistTable(1);
}

/**
 * updateTableNames updates the header names for the product history and dimm sorting tables.
 */
function updateTableNames() {
  //get product history table HTML element and create header elements
  const productHistTable = document.getElementById('productHistTable');
  const productHistTableHeader = document.createElement('thead');
  const productHistTableHeaderRow = document.createElement('tr');

  //add each header to the HTML table, and set each header's sorting function
  headers = ['Customer', 'Date', 'Part Number', 'Dimm Density', 'Total Count', 'Fail Count', 'Fail Rate'];
  for (let i = 0; i < headers.length; i++) {
    var productHistTableHeaderEntry = document.createElement('th');
    productHistTableHeaderEntry.innerText = headers[i];
    productHistTableHeaderEntry.setAttribute('onclick', 'sortproductHistTable(' + i + ')');
    productHistTableHeaderRow.append(productHistTableHeaderEntry);
  }
  productHistTableHeader.append(productHistTableHeaderRow);
  productHistTable.append(productHistTableHeader);

  //update siteheader to include the current dimm type in the top left corner
  const SiteHeader = document.getElementsByClassName('logo-text')[0];
  oldDimmDie = SiteHeader.innerText.split('- ')[1];
  if (oldDimmDie === undefined) {
    oldDimmDie = DimmDie;
  } else {
    oldDimmDie = oldDimmDie.substr(0, 2) + oldDimmDie[2].toLowerCase();
  }
  SiteHeader.innerText = 'PST ANALYTICS DASHBOARD - ' + DimmDie;
}

/**
 * getDataFromSPList goes through and grabs all data needed from the complete aging sharepoint list.
 */
function getDataFromSPList() {

  //create enumerator and arrs for various important stats
  var enumerator = returnedItemsAgingComplete.getEnumerator();

  //go through every item from SP list
  while(enumerator.moveNext()) {

    //get current item and get the Quantity of DIMMS and the customer name
    var listItem = enumerator.get_current();
    var totalDimmCount = parseInt(listItem.get_item('Qty')) ? parseInt(listItem.get_item('Qty')) : 0;
    var customerCurr = listItem.get_item('Title');

    //if there are no Dimms or the customer/batch name is 'combine', then we skip this item
    if (listItem.get_item('Batch').toUpperCase().includes('COMBINE') || !totalDimmCount || customerCurr.toUpperCase().includes('COMBINE')) {
      continue;
    }

    //get important info from list item
    var FailedDimmCount = parseInt(listItem.get_item('Failed_x0020_Qty')) ? parseInt(listItem.get_item('Failed_x0020_Qty')) : 0;
    var dimmCurr = listItem.get_item('Part_x0020_Number');
    var dateCurr = listItem.get_item('Received_x0020_by_x0020_SCM');
    var dateCurrOG = dateCurr;

    //A lot of these customer names are dupes, so we lazily sort through and fix these
    customerCurr = fixcustomerName(customerCurr);

    //if there is a valid date, convert to datetime object, then a string of said date.
    var dateCurrStr = '';
    if (dateCurr) {
      dateCurr = dateCurrOG.split(' ');
      dateCurr = new Date(dateCurr[0]);
      if (dateCurr.getTime()) {
        dateCurrStr = dateCurr.toISOString().split('T')[0];
      } else {
        dateCurr = null;
      }
    }

    //this code makes a dict that contains the fail/total count in the order of dimm -> name.
    //if dimm isn't in dimmdict yet and the date is valid, we add the dimm
    if (dateCurr && !(dimmCurr in dimmDict)) {
      dimmDict[dimmCurr] = {};
    }

    //if date is valid and dateStr is in dimmDict, we update the failedCount and totalCount for the pre-existing dict entry.
    if (dateCurr && !(dateCurrStr in dimmDict[dimmCurr])) {
      dimmDict[dimmCurr][dateCurrStr] = {};
      dimmDict[dimmCurr][dateCurrStr]['failedCount'] = 0;
      dimmDict[dimmCurr][dateCurrStr]['totalCount'] = 0;
    }
    if (dateCurr) {
      dimmDict[dimmCurr][dateCurrStr]['failedCount'] += FailedDimmCount;
      dimmDict[dimmCurr][dateCurrStr]['totalCount'] += totalDimmCount;
      if (!(datesFailedDimmArr.includes(dateCurrStr)) && FailedDimmCount != 0) {
        datesFailedDimmArr.push(dateCurrStr);
      }
    }

    //this code makes a dict that contains the fail/total count in the order of customer -> date -> dimm.
    //create customer dict if it doesn't exist in tabledict.
    if (!(customerCurr in tableDict)) {
      tableDict[customerCurr] = {};
      tableDict[customerCurr]['OverallFailedCount'] = 0;
      tableDict[customerCurr]['OverallTotalCount'] = 0;
    }
    tableDict[customerCurr]['OverallFailedCount'] += FailedDimmCount;
    tableDict[customerCurr]['OverallTotalCount'] += totalDimmCount;
    //create date dict if it doesn't exist in tabledict and date is valid.
    if (dateCurr && !(dateCurrStr in tableDict[customerCurr])) {
      tableDict[customerCurr][dateCurrStr] = {};
    }
    //add to failedCount and totalCount if dimm is in tableDict and date is valid.
    if (dateCurr && !(dimmCurr in tableDict[customerCurr][dateCurrStr])) {
      //create dimm dict if it doesn't exist in tabledict and date is valid. Then create failedCount, totalCount, and record Dimm Density size.
      tableDict[customerCurr][dateCurrStr][dimmCurr] = {};
      tableDict[customerCurr][dateCurrStr][dimmCurr]['failedCount'] = 0;
      tableDict[customerCurr][dateCurrStr][dimmCurr]['totalCount'] = 0;
      tableDict[customerCurr][dateCurrStr][dimmCurr]['DimmDensity'] = listItem.get_item('Dimm_x0020_Density');
    }
    if (dateCurr) {
      tableDict[customerCurr][dateCurrStr][dimmCurr]['failedCount'] += FailedDimmCount;
      tableDict[customerCurr][dateCurrStr][dimmCurr]['totalCount'] += totalDimmCount;
    }
  }
}

/**
 * updateLineChart creates the line chart and inserts all data, headers, etc. for said chart.
 */
function updateLineChart() {

    //sort dates in ascending order
    datesFailedDimmArr.sort(function(a,b) {
      return new Date(a) - new Date(b);
    })
    
    //rebuild first chart canvas
    var chartContainer1canvas = document.createElement('canvas');
    chartContainer1canvas.id = 'mychartLine';
    chartContainer1canvas.setAttribute('style', 'overflow-y: scroll');
    document.getElementById('chart-container-1').append(chartContainer1canvas);
    
    //create GUI line chart
    var mychartLine = new Chart(document.getElementById('mychartLine').getContext('2d'), {
      type: 'line',
      data: {
        labels: datesFailedDimmArr,
        datasets: []
      },
    options: {
      legend: {
        labels: {
          fontColor: '#FFFFFF'
        },
      },
      responsive: true,
      tooltips: {
        mode: 'index',
        intersect: false,
      },
     hover: {
        mode: 'nearest',
        intersect: true
      },
      scales: {
        xAxes: [{
          display: true,
          scaleLabel: {
            display: true,
            labelString: 'Date',
            fontColor: '#FFFFFF'
          },
          ticks: {
            fontColor: '#FFFFFF'
          }
        }],
        yAxes: [{
          display: true,
          scaleLabel: {
            display: true,
            labelString: 'Fail Rate - PPM',
            fontColor: '#FFFFFF'
          },
          ticks: {
            fontColor: '#FFFFFF'
          }
        }]
      },
      }
    });
  
    //if Dimm Type radio buttons haven't been created yet, create them
    if (!tagsPrevious) {
      dropdownUpdateRadio(dropdowns[0], 'D1x');
      dropdownUpdateRadio(dropdowns[0], 'D1y');
      dropdownUpdateRadio(dropdowns[0], 'D1z');
    }
  
    //get # of dimms we are going to display to line chart for later color calculation
    var dimmCount = 0;
    for (var key in dimmDict) {
      if (Object.keys(dimmDict[key]).length != 0) {
        if (PartNumbers.length == 0) {
          dimmCount = dimmCount + 1;
        } else if (PartNumbers.includes(key)) {
          dimmCount = dimmCount + 1;
        }
      }  
    }
  
    //if dimm count is 0, then we are on a different dimm type, so we just use the size of dimmDict for the number of dimms since all dimms will be displayed
    if (dimmCount === 0) {
      PartNumbers = [];
      dimmCount = Object.keys(dimmDict).length;
    }
  
    //this code makes the overhead line chart labels in the GUI for each DIMM
    var counter = 0;
    var colors = palette('cb-GnBu', dimmCount);
  
    //we need an easy way to access TTF times to add them to our chart headers, so we create agingDict.
    var agingDict = {};

    //we then go through the aging error log list entries to get the TTF for each Dimm.
    agingLogEnum = returnedItemsAgingLog.getEnumerator();
    while(agingLogEnum.moveNext()) {

      //get dimm name and corresponding ttf
      var agingDimm = agingLogEnum.get_current().get_item('Part_x0020_No_x002e_');
      var agingTTF = agingLogEnum.get_current().get_item('TTF');

      //if ttf time is invalid, continue to next entry
      if (!convertTimeStringToMS(agingTTF)) {
        continue;
      }

      //if agingDimm is in our dimmDict, then we add the TTF to the agingDict.
      if (agingDimm in dimmDict) {
        if (!(agingDimm in agingDict)) {
          agingDict[agingDimm] = [];
        }
        agingDict[agingDimm].push(agingTTF);
      }
    }
  
    //array of the average TTF for each DIMM
    var avgTTFArr = [];
  
    //this code creates the dataset for the line chart for each DIMM
    for (var key in dimmDict) {
  
      //dimm has no dates, so skip it
      if (Object.keys(dimmDict[key]).length === 0) {
        continue;
      }
  
      //make an array of the PPM for every date for each DIMM
      var failedValsChart = []
      for (let i = 0; i < datesFailedDimmArr.length; i++) {
        if (dimmDict[key][datesFailedDimmArr[i]] && dimmDict[key][datesFailedDimmArr[i]]['failedCount'] > 0) {
          failedValsChart.push(parseInt(dimmDict[key][datesFailedDimmArr[i]]['failedCount'] / dimmDict[key][datesFailedDimmArr[i]]['totalCount'] * 1000000));
        } else {
          failedValsChart.push(0);
        }
      }
      //if every entry for DIMM is 0, we skip adding it to the table
      if (failedValsChart.every(item => item === 0)) {
        continue;
      }
  
      //add dimm to dropdown
      dropdownUpdateCheckBox(dropdowns[1], key);
  
      //if the dimm is not in the partNumbers array, we skip adding it to the table
      if (PartNumbers.length > 0 && !(PartNumbers.includes(key))) {
        continue;
      }
  
      //create the label for the line chart legend for the current DIMM. This label includes the dimm name and TTF.
      var labelLineChart = '';
      var averageTTF = 0;
      if (key in agingDict) {
        //calculate averageTTF and put it in line chart labels and avgTTFArr
        for (let i = 0; i < agingDict[key].length; i++) {
          averageTTF += convertTimeStringToMS(agingDict[key][i]);
        }
        averageTTF = averageTTF / agingDict[key].length;
        labelLineChart = key + ' - ' + convertTimeMSToString(averageTTF);
        avgTTFArr.push(averageTTF);
      } else {
        labelLineChart = key + " - N/A";
      }
  
      //push dataset to chart
      mychartLine.data.datasets.push({
        label: labelLineChart,
          data: failedValsChart,
          lineTension: 0,
          fill: false,
          borderColor: '#' + colors[counter],
          backgroundColor: '#' + colors[counter],
          pointRadius : "4",
          borderWidth: counter + 1,
      });
      counter = counter + 1;

    }

    //update chart and calculate overall average TTF
    mychartLine.update();  
    avgTTF = parseInt(avgTTFArr.reduce((partialSum, a) => partialSum + a, 0) / avgTTFArr.length);
    
}

/**
 * updateDonutChartTable sorts the data needed for the donut chart. It then creates the donut chart and its accompanying percentage table.
 */
function updateDonutChartTable() {

  //sort customerTotalDimmArr by dimm count
  customerTotalDimmArr.sort(function(a, b) {
    return b.totalDimmCount - a.totalDimmCount;
  });

  //then insert data from customerTotalDimmArr to individual arrays
  var customerNamesArr = [];
  var totalDimmCountArr = [];
  for (let i = 0; i < customerTotalDimmArr.length; i++) {
    if (customerTotalDimmArr[i].totalDimmCount === 0) {
      continue;
    }
    customerNamesArr.push(customerTotalDimmArr[i].customer);
    totalDimmCountArr.push(customerTotalDimmArr[i].totalDimmCount);
  }

  //generate label color
  backgroundColorDonut = palette('cb-Blues', 5);
  for (let i = 0; i < 5; i++) {
    backgroundColorDonut[i] = '#' + backgroundColorDonut[i];
  }

  //if there are more than 5 customer entries, we combine all the small entries into a 5th "other" entry
  if (customerNamesArr.length > 5) {

    //get sum of other dimms
    var otherSum = totalDimmCountArr.slice(5, totalDimmCountArr.length).reduce((partialSum, a) => partialSum + a, 0);

    //trim TotaldimmCountArr to 5 entries
    var totalDimmCountArrTemp = totalDimmCountArr.slice(0, 4);
    totalDimmCountArrTemp.push(otherSum);
    totalDimmCountArr = totalDimmCountArrTemp;

    //trim customerNamesArr to 5 entries
    var customerNamesArrTemp = customerNamesArr.slice(0, 4);
    customerNamesArrTemp.push('Other');
    customerNamesArr = customerNamesArrTemp;
  }
  

  //create canvas for donut chart and insert it
  var chartContainer2canvas = document.createElement('canvas');
  chartContainer2canvas.id = 'mychartDonut';
  chartContainer2canvas.setAttribute('style', 'overflow-y: scroll');
  document.getElementById('chart-container-2').append(chartContainer2canvas);

  //create pie chart of total % of dimms by each customer
  new Chart(document.getElementById("mychartDonut").getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: customerNamesArr,
      datasets: [{
        backgroundColor: backgroundColorDonut,
        data: totalDimmCountArr,
        borderWidth: [1, 1, 1, 1, 1]
      }]
    },
  options: {
    maintainAspectRatio: false,
    responsive: true,
    tooltips: {
      mode: 'index',
      intersect: false,
    },
   hover: {
      mode: 'nearest',
      intersect: true
    },
      legend: {
      position :"bottom",	
      display: false,
        labels: {
        fontColor: '#ddd',  
        boxWidth:15
        }
    }
    ,
    tooltips: {
      displayColors:false
    }
      }
  });

  //create labels table for pie chart
  const table2Div = document.getElementById('pieChart');
  const table2 = document.createElement('table');

  //update header name of table and create table body
  document.getElementById('pieTableHeader').innerText = DimmDie + ' Quantity Proportion by Customers';
  table2.className = 'table align-items-center';
  table2Body = document.createElement('tbody');

  //add each customer name and dimm count % to table
  for (let i = 0; i < customerNamesArr.length; i++) {
    table2row = document.createElement('tr');

    //insert background color
    table2i = document.createElement('i');
    table2i.className = "fa fa-circle mr-2";
    table2i.style.color = backgroundColorDonut[i];

    //insert customer name
    table2name = document.createElement('td');
    table2name.innerText = customerNamesArr[i];
    table2name.prepend(table2i);

    //insert total dimm %
    table2percent = document.createElement('td');
    table2percent.innerText = parseFloat((totalDimmCountArr[i] * 100) / sumTotal).toFixed(2) + "%";

    //append entries to table
    table2row.append(table2name);
    table2row.append(table2percent);
    table2Body.append(table2row);
  }

  //append to HTML file
  table2.append(table2Body);
  table2Div.append(table2);
}

/**
 * updateProductHistoryTable inserts data into the product history table page.
 */
function updateProductHistoryTable() {
  
  var ppmArr = [];

  //iterate through every entry of tableDict and insert it into table
  for (let keyCustomer in tableDict) {
    //push the current company to customerTotalDimmArr and set its total dimm count to 0
    customerTotalDimmArr.push({'customer': keyCustomer, 'totalDimmCount': 0});
    for (let keyDate in tableDict[keyCustomer]) {
      //if an entry isn't actually a date, we skip inserting it
      if (!(new Date(keyDate).getTime())) {
        continue;
      }
      for (let keyDimm in tableDict[keyCustomer][keyDate]) {

        const productHistTableBody = document.createElement('tbody');

        if ((PartNumbers.length == 0 || PartNumbers.includes(keyDimm) || oldDimmDie != DimmDie) && tableDict[keyCustomer][keyDate][keyDimm]['failedCount'] != 0) {
          //create table body and row
          var productHistTableRow = document.createElement('tr');

          //insert customer name
          var productHistTableCustomer = document.createElement('td');
          productHistTableCustomer.innerText = keyCustomer;

          //insert date
          var productHistTableDate = document.createElement('td');
          productHistTableDate.innerText = keyDate;

          var productHistTablePartNumber = document.createElement('td');
          productHistTablePartNumber.innerText = keyDimm;

          var productHistTableType = document.createElement('td');
          productHistTableType.innerText = tableDict[keyCustomer][keyDate][keyDimm]['DimmDensity'];

          //insert total dimm count
          var productHistTableTotalCount = document.createElement('td');
          productHistTableTotalCount.innerText = tableDict[keyCustomer][keyDate][keyDimm]['totalCount'];

          //insert fail dimm count
          var productHistTableFailCount = document.createElement('td');
          productHistTableFailCount.innerText = tableDict[keyCustomer][keyDate][keyDimm]['failedCount'];

          //insert dimm fail rate by ppm, and save ppm to ppm Arr for later
          var productHistTableFailRate = document.createElement('td');
          tableDict[keyCustomer][keyDate][keyDimm]['ppm'] = parseInt(tableDict[keyCustomer][keyDate][keyDimm]['failedCount'] / tableDict[keyCustomer][keyDate][keyDimm]['totalCount'] * 1000000);
          ppmArr.push(tableDict[keyCustomer][keyDate][keyDimm]['ppm']);
          productHistTableFailRate.innerText = tableDict[keyCustomer][keyDate][keyDimm]['ppm'] + "ppm";

          //append entries to table
          productHistTableRow.append(productHistTableCustomer);
          productHistTableRow.append(productHistTableDate);
          productHistTableRow.append(productHistTablePartNumber);
          productHistTableRow.append(productHistTableType);
          productHistTableRow.append(productHistTableTotalCount);
          productHistTableRow.append(productHistTableFailCount);
          productHistTableRow.append(productHistTableFailRate);
          productHistTableBody.append(productHistTableRow);
          productHistTable.append(productHistTableBody);

        }

        //update total dimm count for each company for the donut chart later on
        if (PartNumbers.length == 0 || (PartNumbers.length != 0 && oldDimmDie != DimmDie)) {
          customerTotalDimmArr[customerTotalDimmArr.length-1]['totalDimmCount'] += parseInt(tableDict[keyCustomer]['OverallTotalCount']);
          sumTotal += parseInt(tableDict[keyCustomer]['OverallTotalCount']);
        } else if (PartNumbers.length != 0 && PartNumbers.includes(keyDimm)) {
          customerTotalDimmArr[customerTotalDimmArr.length-1]['totalDimmCount'] += parseInt(tableDict[keyCustomer][keyDate][keyDimm]['totalCount']);
          sumTotal += parseInt(tableDict[keyCustomer][keyDate][keyDimm]['totalCount']);
        }

      }
    }
  }
  //calculate overall average ppm and save it for later selected parts info table
  ppmArrAvg = parseInt(ppmArr.reduce((partialSum, a) => partialSum + a, 0) / ppmArr.length);
}

/**
 * updateSelectedPartsInfoTable creates and inserts the data of the parts info table.
 */
function updateSelectedPartsInfoTable() {
  
  //create fail count card and insert its data and icons
  var failCountCard = document.getElementById('fail-count-card').children[0];
  failCountCard.innerText = ppmArrAvg + ' PPM';
  var failCountSpan = document.createElement('span');
  var failCountI = document.createElement('i');
  failCountSpan.className = "float-right";
  failCountI.className = "zmdi zmdi-grid-off";
  failCountSpan.append(failCountI);
  failCountCard.append(failCountSpan);
  
  //create average ttf card and insert its data and icons
  var ttfCard = document.getElementById('ttf-card').children[0];
  ttfCard.innerText = convertTimeMSToString(avgTTF).split(" ")[0];
  var ttfCardSpan = document.createElement('span');
  var ttfCardI = document.createElement('i');
  ttfCardSpan.className = "float-right";
  ttfCardI.className = "zmdi zmdi-time";
  ttfCardSpan.append(ttfCardI);
  ttfCard.append(ttfCardSpan);

  //create total count card and insert its data and icons
  var totalCountCard = document.getElementById('total-count-card').children[0];
  totalCountCard.innerText = sumTotal;
  var totalCountSpan = document.createElement('span');
  var totalCountI = document.createElement('i');
  totalCountSpan.className = "float-right";
  totalCountI.className = "zmdi zmdi-grid";
  totalCountSpan.append(totalCountI);
  totalCountCard.append(totalCountSpan);
}


/**
 * executed if sharepoint CAML query fails
 */
function failed() {
  console.log('Failure: ' + arguments.get_message() + '\n' + arguments.get_stackTrace());
}

/**
 * fixes different duplicate customer names
 */
function fixcustomerName(customer) {
  if (customer.includes("AMD") || customer.includes("ADVANCED MICRO DEVICES")) {
    customer = "AMD";
  } else if (customer.toUpperCase().includes("CISCO")) {
    customer = "CISCO";
  } else if (customer.toUpperCase().includes("GOOG") || customer.toUpperCase().includes("GG")) {
    customer = "GOOGLE";
  } else if (customer.toUpperCase().includes("MICROSOFT")) {
    customer = "MICROSOFT";
  } else if (customer.toUpperCase().includes("APPL")) {
    customer = "APPLE";
  } else if (customer.toUpperCase().includes("DELL")) {
    customer = "DELL";
  } else if (customer.toUpperCase().includes("MITAC")) {
    customer = "MITAC";
  } else if (customer.toUpperCase().includes("IBM")) {
    customer = "IBM";
  } else if (customer.toUpperCase().includes("SOFTLAYER")) {
    customer = "SOFTLAYER";
  } else if (customer.toUpperCase().includes("HP")) {
    customer = "HP";
  } else if (customer.toUpperCase().includes("GIGA")) {
    customer = "GIGABYTE";
  } else if (customer.toUpperCase().includes("INTEL")) {
    customer = "INTEL";
  } else if (customer.toUpperCase().includes("TWITTER")) {
    customer = "TWITTER";
  } else if (customer.toUpperCase().includes("LENOVO")) {
    customer = "LENOVO";
  } else if (customer.toUpperCase().includes("HEWLETT") || customer.toUpperCase().includes("PACKARD") || customer.toUpperCase().includes("HP")) {
    customer = "HP";
  } else if (customer.toUpperCase().includes("LENOVO")) {
    customer = "LENOVO";
  } else if (customer.toUpperCase().includes("SUPERMICRO")) {
    customer = "SUPERMICRO";
  } else if (customer.toUpperCase().includes("FB") || customer.toUpperCase().includes("FACEBOOK") || customer.toUpperCase().includes("META")) {
    customer = "META";
  }
  return customer;
}

/**
 * gets the dropdown elements so they can be updated with info later
 */
function getDropdowns(numDropDowns) {
  var DropDowns = [];
  for(let i = 1; i <= numDropDowns; i++) {
    var tag = 'dropdown' + i;
    DropDowns.push(document.getElementById(tag));
  }
  return DropDowns;
}

/**
 * updates dropdown checkboxes
 */
function dropdownUpdateCheckBox(dropdown, text) {
  var dropdownLI = document.createElement('li');
  var dropdownLabel = document.createElement('label');
  dropdownLabel.setAttribute('style', 'color:white');
  dropdownLabel.innerText = text;
  var dropdownInput = document.createElement('input');
  dropdownInput.setAttribute('type', 'checkbox');
  if (PartNumbers.includes(text)) {
    dropdownInput.checked = true;
  }
  dropdownLabel.prepend(dropdownInput);
  dropdownLI.append(dropdownLabel);
  dropdown.append(dropdownLI);
}

/**
 * updates dropdown radio boxes
 */
function dropdownUpdateRadio(dropdown, text) {
  var dropdownLI = document.createElement('li');
  var dropdownLabel = document.createElement('label');
  dropdownLabel.setAttribute('class', 'form-check-label');
  var forTag = 'flexRadioDefault' + radioCount;
  radioCount = radioCount + 1;
  dropdownLabel.setAttribute('for', forTag);
  dropdownLabel.setAttribute('style', 'color:white');
  dropdownLabel.innerText = text;
  var dropdownInput = document.createElement('input');
  dropdownInput.setAttribute('class', 'form-check-label');
  dropdownInput.setAttribute('type', 'radio');
  dropdownInput.setAttribute('name', 'flexRadioDefault');
  dropdownInput.setAttribute('id', forTag);
  if (DimmDie === text) {
    dropdownInput.checked = true;
  }
  dropdownLabel.prepend(dropdownInput);
  dropdownLI.append(dropdownLabel);
  dropdown.append(dropdownLI);
}

/**
 * applySettings updates all the tables/graphs/dropdowns to reflect the newly selected dimm type and part numbers.
 */
function applySettings() {

  //since we don't want to update some stuff, we set tagsPrevious to true. the default DimmDie is set as well
  tagsPrevious = true;
  DimmDieTemp = 'D1x';
  var partNumbersTemp = [];

  //update dimmdie dropdown box entries
  var items = document.getElementsByTagName('input');
  for (let i = 0; i < items.length; i++) {
    if (items[i].type === 'radio' ) {
      if (items[i].checked) {
        DimmDieTemp = items[i].parentElement.innerText;
      }
    } else if (items[i].type === 'checkbox') {
      if (items[i].checked) {
        partNumbersTemp.push(items[i].parentElement.innerText);
      }
    }
  }

  //destroy any garbage residual chartjs monitor elements
  while (document.querySelector('div.chartjs-size-monitor')) {
    document.querySelector('div.chartjs-size-monitor').remove();
  }

  //destroy charts
  for (let canvas of document.getElementsByTagName('canvas')) {
    canvas.remove();
  }
  for (let canvas of document.getElementsByTagName('canvas')) {
    canvas.remove();
  }

  //get all table entries
  const table2Div = document.getElementById('pieChart');
  const productHistTable = document.getElementById('productHistTable');
  const dropdown2 = document.getElementById('dropdown2');

  //destroy all table entries of pie chart table
  while (table2Div.firstChild) {
    table2Div.removeChild(table2Div.firstChild);
  }

  //destroy all table entries of the main Product History Table (except for the header)
  while (productHistTable.firstChild) {
      productHistTable.removeChild(productHistTable.firstChild);
  }


  //destroy all dropdown labels
  while (dropdown2.firstChild) {
    dropdown2.removeChild(dropdown2.firstChild);
  }

  //reimport tables/graphs/etc.
  listImport(DimmDieTemp, partNumbersTemp);
}

/**
 * sortproductHistTable sorts the product history table based on the header that was clicked.
 * 
 * @param {*} n index of header to be sorted by
 */
function sortproductHistTable(n) {

  //initialize variables and get table
  var productHistTableRows, currRowText, nextRowText, shouldSwitch, i;
  var numSwaps = 0;
  var productHistTable = document.getElementById("productHistTable");
  var allowSwap = true;
  var sortDirection = "sortDescending";

  while (allowSwap) {

    allowSwap = false;
    productHistTableRows = productHistTable.rows;

    //compare every row until we find two rows to swap
    for (i = 1; i < (productHistTableRows.length - 1); i++) {
      shouldSwitch = false;
      currRowText = productHistTableRows[i].getElementsByTagName("TD")[n].innerHTML.toLowerCase();
      nextRowText = productHistTableRows[i + 1].getElementsByTagName("TD")[n].innerHTML.toLowerCase();
      if (sortDirection === "sortAscending") {
        if (n === 3) {

          //special cases for different columns
          if (parseInt(currRowText.split("gb")) > parseInt(nextRowText.split("gb"))) {
            shouldSwitch = true;
            break;
          }
        } else if (n === 4 || n === 5) {

          if (parseInt(currRowText) > parseInt(nextRowText)) {
            shouldSwitch = true;
            break;
          }
        } else if (n === 6) {

          if (parseInt(currRowText.split("ppm")) > parseInt(nextRowText.split("ppm"))) {
            shouldSwitch = true;
            break;
          }
        } else {

          if (currRowText > nextRowText) {
            shouldSwitch = true;
            break;
          }
        }
      } else if (sortDirection === "sortDescending") {
        
        //special cases for different columns
        if (n === 3) {

          if (parseInt(currRowText.split("gb")) < parseInt(nextRowText.split("gb"))) {
            shouldSwitch = true;
            break;
          }
        } else if (n === 4 || n === 5) {

          if (parseInt(currRowText) < parseInt(nextRowText)) {
            shouldSwitch = true;
            break;
          }
        } else if (n === 6) {

          if (parseInt(currRowText.split("ppm")) < parseInt(nextRowText.split("ppm"))) {
            shouldSwitch = true;
            break;
          }
        } else {

          if (currRowText < nextRowText) {
            shouldSwitch = true;
            break;
          }
        }
      }
    }

    //a swap has been found, so we swap the two rows and continue
    if (shouldSwitch) {

      productHistTableRows[i].parentNode.insertBefore(productHistTableRows[i + 1], productHistTableRows[i]);
      allowSwap = true;
      numSwaps = numSwaps + 1;
    } else {

      //if no swaps were made while in descending mode, then that means the table was already in a descending order.
      //so we instead try to sort again in the ascending direction.
      if (numSwaps == 0 && sortDirection == "sortDescending") {
        sortDirection = "sortAscending";
        allowSwap = true;
      }
    }
  }

  //update the currently sorted header to show whether it is ascending or descending, and remove arrow for old sorted headers 
  for (let j = 0; j < 7; j++) {
    var updateName = document.getElementById("productHistTable").rows[0].getElementsByTagName("TH")[j];
    updateName.innerText = updateName.innerText.split(' -')[0];
    if (j == n) {
      if (sortDirection == "sortAscending") {
        updateName.innerText = updateName.innerText.split(' -')[0] + ' - ' + '↑';
      } else {
        updateName.innerText = updateName.innerText.split(' -')[0] + ' - ' + '↓';
      }
    }
  }
}

/**
 * AgingErrorLogImport imports the aging error log list from sharepoint using a CAML query.
 * 
 * @returns executes updatePage function if CAML query is successful, or failed function if unsuccessful
 */
function AgingErrorLogImport () {
  var ctx = new SP.ClientContext(urlSP);
  var listName = "Aging Error log";
  var oList = ctx.get_web().get_lists().getByTitle(listName);
  var caml = new SP.CamlQuery();
  caml.set_viewXml("<View><RowLimit>0</RowLimit></View>");
  returnedItemsAgingLog = oList.getItems(caml);
  ctx.load(returnedItemsAgingLog);
  return ctx.executeQueryAsync(updatePage, failed);
}

/**
 * convertTimeStringToMS converts a string in the format of DD:HH:MM:SS to milliseconds.
 * @param {*} time time as string in DD:HH:MM:SS format
 * @returns milliseconds
 */
function convertTimeStringToMS(time) {
  //if time format isn't correct, return
  if (!time) {
    return 0;
  }

  //split time string into arrau
  arrTime = time.split(':');
  var days = 0;
  var hours = 0;
  var mins = 0;
  var secs = 0;

  //break down string into days/hours/mins/secs
  if (arrTime.length === 4) {
    days = parseInt(arrTime[0]);
    hours = parseInt(arrTime[1]);
    mins = parseInt(arrTime[2]);
    secs = parseInt(arrTime[3]);

  } else if (arrTime.length === 3) {
    hours = parseInt(arrTime[0]);
    mins = parseInt(arrTime[1]);
    secs = parseInt(arrTime[2]);

  } else if (arrTime.length === 2) {
    mins = parseInt(arrTime[0]);
    secs = parseInt(arrTime[1]);

  } else if (arrTime.length === 1) {
    secs = parseInt(arrTime[0]);
  }

  //calculate and return milliseconds
  return (1000 * ((days * 24 * 60 * 60) + (hours * 60 * 60) + (mins * 60) + (secs)));
}
/**
 * convertTimeStringToMS converts int of milliseconds to string in the format of DD:HH:MM:SS.
 * @param {*} time int of milliseconds
 * @returns string in format of DD:HH:MM:SS
 */
function convertTimeMSToString(time) {
  //convert from milliseconds to seconds
  time = time / 1000;

  //get days/hours/mins/secs
  var days = Math.floor(time / (24 * 60 * 60));
  var hours =  Math.floor((time - (days * 24 * 60 * 60)) / (60 * 60));
  var mins =  Math.floor((time - ((days * 24 * 60 * 60) + (hours * 60 * 60))) / 60);
  var secs =  Math.floor((time - ((days * 24 * 60 * 60) + (hours * 60 * 60) + (mins * 60))));

  //build and return string based on day/hour/min/sec values
  if (days && hours && mins && secs) {
    return (padZero(days) + ':' +  padZero(hours) + ':' +  padZero(mins) + ':' +  padZero(secs) + ' average TTF');
  } else if (hours && mins && secs) {
    return (padZero(hours) + ':' +  padZero(mins) + ':' +  padZero(secs) + ' average TTF');
  } else if (mins && secs) {
    return (padZero(mins) + ':' +  padZero(secs) + ' average TTF');
  } else if (secs) {
    return (padZero(secs) + ' average TTF');
  } else {
    return 'N/A';
  }
}

/**
 * used for padding time string.
 * 
 * For example, if we have 7, we want to format to 07 for time string.
 * 
 * @param {*} num number we want to format
 * @returns number as formatted string
 */
function padZero(num) {
  num = num.toString();
  while (num.length < 2) {
    num = "0" + num;
  }
  return num;
}