<!DOCTYPE html>
<html lang="en">
  <head>
    <script type="text/javascript" src="/_layouts/1033/init.js"></script>
    <script type="text/javascript" src="/_layouts/15/MicrosoftAjax.js"></script>
    <script src="/_layouts/15/sp.core.js" type="text/javascript"></script>
    <script src="/_layouts/15/sp.runtime.js" type="text/javascript"></script>
    <script src="/_layouts/15/sp.js" type="text/javascript"></script>
    <meta name="WebPartPageExpansion" content="full" />
    <meta charset="utf-8"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"/>
    <meta name="description" content=""/>
    <meta name="author" content=""/>
    <meta content="" name="keywords">
    <meta content="" name="description">
    <!--http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/-->
    <title> SSI Dashboard </title>
    <!-- simplebar CSS-->
    <link href="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/plugins/simplebar/css/simplebar.css" rel="stylesheet"/>
    <!-- Bootstrap core CSS-->
    <link href="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/css/bootstrap.min.css" rel="stylesheet"/>
    <!-- animate CSS-->
    <link href="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/css/animate.css" rel="stylesheet" type="text/css"/>
    <!-- Icons CSS-->
    <link href="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/css/icons.css" rel="stylesheet" type="text/css"/>
    <!-- Sidebar CSS-->
    <link href="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/css/sidebar-menu.css" rel="stylesheet"/>
    <!-- Custom Style-->
    <link href="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/css/app-style.css" rel="stylesheet"/>
    <!-- Icon Font Stylesheet -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css" rel="stylesheet">



  </head>


  <!-- Start Sidebar-->
  <body class="bg-theme">

    <div id="wrapper">
      <!--Start sidebar-wrapper-->
      <div id="sidebar-wrapper">
        <div id = "sidebar-wrapper-color">
          <div class="brand-logo">
            <h5 class="logo-text">Data Analytics Dashboard</h5>
          </div>
          <ul class="sidebar-menu do-nicescroll">
            <div class="dropdown">
              <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenu1" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true" style="background-color: transparent; border-color: transparent;">
                <i class="zmdi zmdi-sort-asc" style="font-size: 14px;" style="background-color: transparent; border-color: transparent;"></i>
                <span style="margin-left: 8px; font-size: 14px;" id="mycard" style="background-color: transparent; border-color: transparent;">DIMM Type</span>
              </button>
              <div class="dropdown-menu checkbox-menu allow-focus" aria-labelledby="dropdownMenu1" id="dropdown1">
              </div>
            </div>
            <div class="dropdown">
              <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenu2" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true" style="background-color: transparent; border-color: transparent;">
                <i class="zmdi zmdi-format-list-numbered" style="font-size: 14px;"></i>
                <span style="margin-left: 8px; font-size: 14px;" id="mycard">Part Number</span>
              </button>
              <div class="dropdown-menu checkbox-menu allow-focus" aria-labelledby="dropdownMenu2" id="dropdown2">
              </div>
            </div>
            <button type="button" class="btn btn-secondary" style="background-color: transparent; border-color: white; margin-left: 10px", id="applybutton" onclick="applySettings()">
              <i class="zmdi zmdi-check-all" style="font-size: 14px; margin-left: -10px"></i>
              <span style="margin-left: 8px; font-size: 14px;" id="mycard">
                Apply
              </span>
            </button>
          </ul>
        </div>
        <div class="card-spacing-2"></div>
        <div class="card mt-3">
          <div class="card-content">
            <div class="card-header"> Selected Parts Information
            </div>
              <div class="row row-group m-0" style="border-bottom: 1px solid rgba(255, 255, 255, 0.12);">
                  <div class="card-body" id="total-count-card">
                    <h5 class="text-white mb-0">0</h5>
                    <p class="mb-0 text-white small-font"> Total Count (PCS) </p>
                    </div>
              </div>
                  <div class="row row-group m-0" style="border-bottom: 1px solid rgba(255, 255, 255, 0.12);">
                      <div class="card-body" id="fail-count-card">
                        <h5 class="text-white mb-0">0</h5>
                        <p class="mb-0 text-white small-font"> Average Failure Rate (PPM) </p>
                      </div>
                  </div>
                  <div class="row row-group m-0">
                      <div class="card-body" id="ttf-card">
                        <h5 class="text-white mb-0">0</h5>
                        <p class="mb-0 text-white small-font"> Average TTF (Hour) </p>
                      </div>
                  </div>

          </div>
       </div> 
      </div>
      <div class="content-wrapper" id = "content-wrapper">
        <div class="container-fluid">
          <div class="row">
            <div class="col-12 col-lg-12">
              <div class="card">
                <div class="card-header"> Product History
                  <div class="card-action">
                    <div class="dropdown">
                    </div>
                  </div>
                </div>
                <div class="table-responsive1">
                  <table class="table align-items-center table-flush table-borderless table-hover" id="productHistTable"></table>
                </div>
              </div>
            </div>
          </div>

          &nbsp;
    <!-- Failure Quantity Graph-->
          <div class="row">
            <div class="col-12 col-lg-8 col-xl-8">
              <div class="card">
                <div class="card-header"> Failure Rate Comparison
                </div>
                <div class="card-body">
                  <ul class="list-inline" id = "lineChartTitles">
                  </ul>
                  <div class="chart-container-1" id = "chart-container-1">
                  </div>
                </div>          
              </div>
            </div>

    <!-- Product Quantity Proportion-->
          <div class="col-12 col-lg-4 col-xl-4">
            <div class="card">
              <div class="card-header" id="pieTableHeader">
              </div>
              <div class="card-body">
                <div class="chart-container-2" id = "chart-container-2">
                </div>
              </div>
              <div class="table-responsive2">
                <div class="table align-items-center" id ="pieChart">
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- listImporter Requirements JavaScript-->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.min.js"></script>
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/js/listImporter.js"></script>
    <script src="https://code.jquery.com/jquery-2.2.4.js" type="text/javascript"></script>

    <!-- Bootstrap core JavaScript-->
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/jquery.min.js"></script>
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/popper.min.js"></script>
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/bootstrap.min.js"></script>

    <!-- simplebar js -->
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/plugins/simplebar/js/simplebar.js"></script>

    <!-- sidebar-menu js -->
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/sidebar-menu.js"></script>

    <!-- Custom scripts -->
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/app-script.js"></script>

    <!-- Index js -->
    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/index.js"></script>

    <script src="http://sharepoint.ssi.samsung.com/biz/CQMP/SiteAssets/DashboardPST/assets/js/palette.js"></script>

    <!-- listImport startup -->
    <script>
    $(function () {
    SP.SOD.executeFunc('sp.js', 'SP.ClientContext', loadList);
    function loadList() {
      listImport('D1x', [])
    }
    });
    </script>
  

  
  </body>
</html>