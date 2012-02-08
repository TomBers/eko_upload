var NAVTREE =
[
  [ "eko-sensor-firmware", "index.html", [
    [ "File List", "files.html", [
      [ "PIC24F_Slave/main.c", "main_8c.html", null ],
      [ "PIC24F_Slave/board/chip.h", "chip_8h.html", null ],
      [ "PIC24F_Slave/board/p24_board.h", "p24__board_8h.html", null ],
      [ "PIC24F_Slave/board/p24_fuses.h", "p24__fuses_8h.html", null ],
      [ "PIC24F_Slave/board/p24f16ka102_fuses.h", "p24f16ka102__fuses_8h.html", null ],
      [ "PIC24F_Slave/board/p24fj256gb106_fuses.h", "p24fj256gb106__fuses_8h.html", null ],
      [ "PIC24F_Slave/board/p24_boards/p24_board_devkit.h", "p24__board__devkit_8h.html", null ],
      [ "PIC24F_Slave/board/p24_boards/p24_board_ekobbr2.h", "p24__board__ekobbr2_8h.html", null ],
      [ "PIC24F_Slave/board/p24_boards/p24_board_ekobbr3.h", "p24__board__ekobbr3_8h.html", null ],
      [ "PIC24F_Slave/common/eko_i2c_sensors.c", "eko__i2c__sensors_8c.html", null ],
      [ "PIC24F_Slave/common/i2c_Func.c", "i2c___func_8c.html", null ],
      [ "PIC24F_Slave/common/mb_crc16.c", "mb__crc16_8c.html", null ],
      [ "PIC24F_Slave/common/modbus2.c", "modbus2_8c.html", null ],
      [ "PIC24F_Slave/common/p24_adc.c", "p24__adc_8c.html", null ],
      [ "PIC24F_Slave/common/taos2561.c", "taos2561_8c.html", null ],
      [ "PIC24F_Slave/common/tmr2delay.c", "tmr2delay_8c.html", null ],
      [ "PIC24F_Slave/common/p24/adc.c", "adc_8c.html", null ],
      [ "PIC24F_Slave/common/p24/eko_i2c_sensors.c", "p24_2eko__i2c__sensors_8c.html", null ],
      [ "PIC24F_Slave/common/p24/i2c_engscope.c", "i2c__engscope_8c.html", null ],
      [ "PIC24F_Slave/include/crc_tables.h", "crc__tables_8h.html", null ],
      [ "PIC24F_Slave/include/eko_i2c_sensors.h", "eko__i2c__sensors_8h.html", null ],
      [ "PIC24F_Slave/include/i2c.h", "i2c_8h.html", null ],
      [ "PIC24F_Slave/include/mb_crc16.h", "mb__crc16_8h.html", null ],
      [ "PIC24F_Slave/include/modbus2.h", "modbus2_8h.html", null ],
      [ "PIC24F_Slave/include/p24_adc.h", "p24__adc_8h.html", null ],
      [ "PIC24F_Slave/include/tmr2delay.h", "tmr2delay_8h.html", null ]
    ] ],
    [ "Globals", "globals.html", null ]
  ] ]
];

function createIndent(o,domNode,node,level)
{
  if (node.parentNode && node.parentNode.parentNode)
  {
    createIndent(o,domNode,node.parentNode,level+1);
  }
  var imgNode = document.createElement("img");
  if (level==0 && node.childrenData)
  {
    node.plus_img = imgNode;
    node.expandToggle = document.createElement("a");
    node.expandToggle.href = "javascript:void(0)";
    node.expandToggle.onclick = function() 
    {
      if (node.expanded) 
      {
        $(node.getChildrenUL()).slideUp("fast");
        if (node.isLast)
        {
          node.plus_img.src = node.relpath+"ftv2plastnode.png";
        }
        else
        {
          node.plus_img.src = node.relpath+"ftv2pnode.png";
        }
        node.expanded = false;
      } 
      else 
      {
        expandNode(o, node, false);
      }
    }
    node.expandToggle.appendChild(imgNode);
    domNode.appendChild(node.expandToggle);
  }
  else
  {
    domNode.appendChild(imgNode);
  }
  if (level==0)
  {
    if (node.isLast)
    {
      if (node.childrenData)
      {
        imgNode.src = node.relpath+"ftv2plastnode.png";
      }
      else
      {
        imgNode.src = node.relpath+"ftv2lastnode.png";
        domNode.appendChild(imgNode);
      }
    }
    else
    {
      if (node.childrenData)
      {
        imgNode.src = node.relpath+"ftv2pnode.png";
      }
      else
      {
        imgNode.src = node.relpath+"ftv2node.png";
        domNode.appendChild(imgNode);
      }
    }
  }
  else
  {
    if (node.isLast)
    {
      imgNode.src = node.relpath+"ftv2blank.png";
    }
    else
    {
      imgNode.src = node.relpath+"ftv2vertline.png";
    }
  }
  imgNode.border = "0";
}

function newNode(o, po, text, link, childrenData, lastNode)
{
  var node = new Object();
  node.children = Array();
  node.childrenData = childrenData;
  node.depth = po.depth + 1;
  node.relpath = po.relpath;
  node.isLast = lastNode;

  node.li = document.createElement("li");
  po.getChildrenUL().appendChild(node.li);
  node.parentNode = po;

  node.itemDiv = document.createElement("div");
  node.itemDiv.className = "item";

  node.labelSpan = document.createElement("span");
  node.labelSpan.className = "label";

  createIndent(o,node.itemDiv,node,0);
  node.itemDiv.appendChild(node.labelSpan);
  node.li.appendChild(node.itemDiv);

  var a = document.createElement("a");
  node.labelSpan.appendChild(a);
  node.label = document.createTextNode(text);
  a.appendChild(node.label);
  if (link) 
  {
    a.href = node.relpath+link;
  } 
  else 
  {
    if (childrenData != null) 
    {
      a.className = "nolink";
      a.href = "javascript:void(0)";
      a.onclick = node.expandToggle.onclick;
      node.expanded = false;
    }
  }

  node.childrenUL = null;
  node.getChildrenUL = function() 
  {
    if (!node.childrenUL) 
    {
      node.childrenUL = document.createElement("ul");
      node.childrenUL.className = "children_ul";
      node.childrenUL.style.display = "none";
      node.li.appendChild(node.childrenUL);
    }
    return node.childrenUL;
  };

  return node;
}

function showRoot()
{
  var headerHeight = $("#top").height();
  var footerHeight = $("#nav-path").height();
  var windowHeight = $(window).height() - headerHeight - footerHeight;
  navtree.scrollTo('#selected',0,{offset:-windowHeight/2});
}

function expandNode(o, node, imm)
{
  if (node.childrenData && !node.expanded) 
  {
    if (!node.childrenVisited) 
    {
      getNode(o, node);
    }
    if (imm)
    {
      $(node.getChildrenUL()).show();
    } 
    else 
    {
      $(node.getChildrenUL()).slideDown("fast",showRoot);
    }
    if (node.isLast)
    {
      node.plus_img.src = node.relpath+"ftv2mlastnode.png";
    }
    else
    {
      node.plus_img.src = node.relpath+"ftv2mnode.png";
    }
    node.expanded = true;
  }
}

function getNode(o, po)
{
  po.childrenVisited = true;
  var l = po.childrenData.length-1;
  for (var i in po.childrenData) 
  {
    var nodeData = po.childrenData[i];
    po.children[i] = newNode(o, po, nodeData[0], nodeData[1], nodeData[2],
        i==l);
  }
}

function findNavTreePage(url, data)
{
  var nodes = data;
  var result = null;
  for (var i in nodes) 
  {
    var d = nodes[i];
    if (d[1] == url) 
    {
      return new Array(i);
    }
    else if (d[2] != null) // array of children
    {
      result = findNavTreePage(url, d[2]);
      if (result != null) 
      {
        return (new Array(i).concat(result));
      }
    }
  }
  return null;
}

function initNavTree(toroot,relpath)
{
  var o = new Object();
  o.toroot = toroot;
  o.node = new Object();
  o.node.li = document.getElementById("nav-tree-contents");
  o.node.childrenData = NAVTREE;
  o.node.children = new Array();
  o.node.childrenUL = document.createElement("ul");
  o.node.getChildrenUL = function() { return o.node.childrenUL; };
  o.node.li.appendChild(o.node.childrenUL);
  o.node.depth = 0;
  o.node.relpath = relpath;

  getNode(o, o.node);

  o.breadcrumbs = findNavTreePage(toroot, NAVTREE);
  if (o.breadcrumbs == null)
  {
    o.breadcrumbs = findNavTreePage("index.html",NAVTREE);
  }
  if (o.breadcrumbs != null && o.breadcrumbs.length>0)
  {
    var p = o.node;
    for (var i in o.breadcrumbs) 
    {
      var j = o.breadcrumbs[i];
      p = p.children[j];
      expandNode(o,p,true);
    }
    p.itemDiv.className = p.itemDiv.className + " selected";
    p.itemDiv.id = "selected";
    $(window).load(showRoot);
  }
}

