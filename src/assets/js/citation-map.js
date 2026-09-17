/*
 * Citation world map — draws a choropleth of citing_papers by author country.
 * Data injected via window.__citationMapData = [{country_code, count}, ...]
 */
(function () {
  const container = document.getElementById("citation-map");
  if (!container) return;

  const data = window.__citationMapData || [];
  if (!data.length) {
    container.innerHTML = '<p class="citation-map-empty">国別データがありません</p>';
    return;
  }

  // ISO 3166-1 alpha-2 → numeric (world-atlas uses numeric IDs)
  const A2_TO_NUM = {
    AD:"020",AE:"784",AF:"004",AG:"028",AI:"660",AL:"008",AM:"051",AO:"024",AQ:"010",AR:"032",
    AS:"016",AT:"040",AU:"036",AW:"533",AX:"248",AZ:"031",BA:"070",BB:"052",BD:"050",BE:"056",
    BF:"854",BG:"100",BH:"048",BI:"108",BJ:"204",BL:"652",BM:"060",BN:"096",BO:"068",BQ:"535",
    BR:"076",BS:"044",BT:"064",BV:"074",BW:"072",BY:"112",BZ:"084",CA:"124",CC:"166",CD:"180",
    CF:"140",CG:"178",CH:"756",CI:"384",CK:"184",CL:"152",CM:"120",CN:"156",CO:"170",CR:"188",
    CU:"192",CV:"132",CW:"531",CX:"162",CY:"196",CZ:"203",DE:"276",DJ:"262",DK:"208",DM:"212",
    DO:"214",DZ:"012",EC:"218",EE:"233",EG:"818",EH:"732",ER:"232",ES:"724",ET:"231",FI:"246",
    FJ:"242",FK:"238",FM:"583",FO:"234",FR:"250",GA:"266",GB:"826",GD:"308",GE:"268",GF:"254",
    GG:"831",GH:"288",GI:"292",GL:"304",GM:"270",GN:"324",GP:"312",GQ:"226",GR:"300",GS:"239",
    GT:"320",GU:"316",GW:"624",GY:"328",HK:"344",HM:"334",HN:"340",HR:"191",HT:"332",HU:"348",
    ID:"360",IE:"372",IL:"376",IM:"833",IN:"356",IO:"086",IQ:"368",IR:"364",IS:"352",IT:"380",
    JE:"832",JM:"388",JO:"400",JP:"392",KE:"404",KG:"417",KH:"116",KI:"296",KM:"174",KN:"659",
    KP:"408",KR:"410",KW:"414",KY:"136",KZ:"398",LA:"418",LB:"422",LC:"662",LI:"438",LK:"144",
    LR:"430",LS:"426",LT:"440",LU:"442",LV:"428",LY:"434",MA:"504",MC:"492",MD:"498",ME:"499",
    MF:"663",MG:"450",MH:"584",MK:"807",ML:"466",MM:"104",MN:"496",MO:"446",MP:"580",MQ:"474",
    MR:"478",MS:"500",MT:"470",MU:"480",MV:"462",MW:"454",MX:"484",MY:"458",MZ:"508",NA:"516",
    NC:"540",NE:"562",NF:"574",NG:"566",NI:"558",NL:"528",NO:"578",NP:"524",NR:"520",NU:"570",
    NZ:"554",OM:"512",PA:"591",PE:"604",PF:"258",PG:"598",PH:"608",PK:"586",PL:"616",PM:"666",
    PN:"612",PR:"630",PS:"275",PT:"620",PW:"585",PY:"600",QA:"634",RE:"638",RO:"642",RS:"688",
    RU:"643",RW:"646",SA:"682",SB:"090",SC:"690",SD:"729",SE:"752",SG:"702",SH:"654",SI:"705",
    SJ:"744",SK:"703",SL:"694",SM:"674",SN:"686",SO:"706",SR:"740",SS:"728",ST:"678",SV:"222",
    SX:"534",SY:"760",SZ:"748",TC:"796",TD:"148",TF:"260",TG:"768",TH:"764",TJ:"762",TK:"772",
    TL:"626",TM:"795",TN:"788",TO:"776",TR:"792",TT:"780",TV:"798",TW:"158",TZ:"834",UA:"804",
    UG:"800",UM:"581",US:"840",UY:"858",UZ:"860",VA:"336",VC:"670",VE:"862",VG:"092",VI:"850",
    VN:"704",VU:"548",WF:"876",WS:"882",YE:"887",YT:"175",ZA:"710",ZM:"894",ZW:"716"
  };
  const NUM_TO_A2 = {};
  const NUM_TO_NAME = {
    "004":"Afghanistan","008":"Albania","012":"Algeria","020":"Andorra","024":"Angola",
    "028":"Antigua and Barbuda","031":"Azerbaijan","032":"Argentina","036":"Australia",
    "040":"Austria","044":"Bahamas","048":"Bahrain","050":"Bangladesh","051":"Armenia",
    "052":"Barbados","056":"Belgium","064":"Bhutan","068":"Bolivia","070":"Bosnia and Herzegovina",
    "072":"Botswana","076":"Brazil","084":"Belize","090":"Solomon Islands","096":"Brunei",
    "100":"Bulgaria","104":"Myanmar","108":"Burundi","112":"Belarus","116":"Cambodia",
    "120":"Cameroon","124":"Canada","132":"Cabo Verde","140":"Central African Rep.",
    "144":"Sri Lanka","148":"Chad","152":"Chile","156":"China","158":"Taiwan","170":"Colombia",
    "174":"Comoros","178":"Congo","180":"Dem. Rep. Congo","188":"Costa Rica","191":"Croatia",
    "192":"Cuba","196":"Cyprus","203":"Czechia","208":"Denmark","212":"Dominica",
    "214":"Dominican Rep.","218":"Ecuador","222":"El Salvador","226":"Equatorial Guinea",
    "231":"Ethiopia","232":"Eritrea","233":"Estonia","242":"Fiji","246":"Finland","250":"France",
    "262":"Djibouti","266":"Gabon","268":"Georgia","270":"Gambia","275":"Palestine","276":"Germany",
    "288":"Ghana","292":"Gibraltar","296":"Kiribati","300":"Greece","304":"Greenland","308":"Grenada",
    "316":"Guam","320":"Guatemala","324":"Guinea","328":"Guyana","332":"Haiti","336":"Vatican",
    "340":"Honduras","344":"Hong Kong","348":"Hungary","352":"Iceland","356":"India","360":"Indonesia",
    "364":"Iran","368":"Iraq","372":"Ireland","376":"Israel","380":"Italy","384":"Ivory Coast",
    "388":"Jamaica","392":"Japan","398":"Kazakhstan","400":"Jordan","404":"Kenya","408":"North Korea",
    "410":"South Korea","414":"Kuwait","417":"Kyrgyzstan","418":"Laos","422":"Lebanon","426":"Lesotho",
    "428":"Latvia","430":"Liberia","434":"Libya","438":"Liechtenstein","440":"Lithuania","442":"Luxembourg",
    "446":"Macao","450":"Madagascar","454":"Malawi","458":"Malaysia","462":"Maldives","466":"Mali",
    "470":"Malta","474":"Martinique","478":"Mauritania","480":"Mauritius","484":"Mexico","492":"Monaco",
    "496":"Mongolia","498":"Moldova","499":"Montenegro","504":"Morocco","508":"Mozambique","512":"Oman",
    "516":"Namibia","520":"Nauru","524":"Nepal","528":"Netherlands","540":"New Caledonia","548":"Vanuatu",
    "554":"New Zealand","558":"Nicaragua","562":"Niger","566":"Nigeria","578":"Norway","583":"Micronesia",
    "584":"Marshall Islands","585":"Palau","586":"Pakistan","591":"Panama","598":"Papua New Guinea",
    "600":"Paraguay","604":"Peru","608":"Philippines","616":"Poland","620":"Portugal","624":"Guinea-Bissau",
    "626":"Timor-Leste","630":"Puerto Rico","634":"Qatar","642":"Romania","643":"Russia","646":"Rwanda",
    "659":"Saint Kitts and Nevis","662":"Saint Lucia","670":"Saint Vincent","674":"San Marino",
    "678":"Sao Tome and Principe","682":"Saudi Arabia","686":"Senegal","688":"Serbia","690":"Seychelles",
    "694":"Sierra Leone","702":"Singapore","703":"Slovakia","704":"Vietnam","705":"Slovenia",
    "706":"Somalia","710":"South Africa","716":"Zimbabwe","724":"Spain","728":"South Sudan",
    "729":"Sudan","732":"W. Sahara","740":"Suriname","748":"Eswatini","752":"Sweden","756":"Switzerland",
    "760":"Syria","762":"Tajikistan","764":"Thailand","768":"Togo","776":"Tonga","780":"Trinidad and Tobago",
    "784":"UAE","788":"Tunisia","792":"Turkey","795":"Turkmenistan","798":"Tuvalu","800":"Uganda",
    "804":"Ukraine","807":"North Macedonia","818":"Egypt","826":"United Kingdom","834":"Tanzania",
    "840":"United States","850":"US Virgin Islands","854":"Burkina Faso","858":"Uruguay",
    "860":"Uzbekistan","862":"Venezuela","882":"Samoa","887":"Yemen","894":"Zambia"
  };
  Object.keys(A2_TO_NUM).forEach(k => { NUM_TO_A2[A2_TO_NUM[k]] = k; });

  const countByNum = {};
  data.forEach(d => {
    const num = A2_TO_NUM[d.country_code];
    if (num) countByNum[num] = d.count;
  });

  const maxCount = Math.max(...data.map(d => d.count));

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = resolve;
      s.onerror = () => reject(new Error("failed to load " + src));
      document.head.appendChild(s);
    });
  }

  async function render() {
    if (!window.d3) {
      await loadScript("https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js");
    }
    if (!window.topojson) {
      await loadScript("https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js");
    }
    const world = await d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json");
    draw(world);
  }

  function draw(world) {
    const width = container.clientWidth || 900;
    const height = Math.round(width * 0.5);

    const svg = d3.select(container).append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("width", "100%")
      .style("height", "auto")
      .style("background", "#f8fafc");

    const projection = d3.geoNaturalEarth1()
      .fitSize([width, height], topojson.feature(world, world.objects.countries));
    const path = d3.geoPath(projection);

    // 対数スケール（1件と38件の差が視覚的に潰れないように）
    const color = d3.scaleSequential()
      .domain([0, Math.log(maxCount + 1)])
      .interpolator(d3.interpolateBlues);

    const countries = topojson.feature(world, world.objects.countries).features;

    const tooltip = d3.select(container).append("div")
      .attr("class", "citation-map-tooltip")
      .style("position", "absolute")
      .style("pointer-events", "none")
      .style("opacity", 0);

    // Wrap container to allow absolute-positioned tooltip
    container.style.position = "relative";

    svg.append("g")
      .selectAll("path")
      .data(countries)
      .join("path")
      .attr("d", path)
      .attr("fill", d => {
        const n = countByNum[String(d.id).padStart(3, "0")] || 0;
        return n > 0 ? color(Math.log(n + 1)) : "#e5e7eb";
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.5)
      .on("mousemove", function (event, d) {
        const id = String(d.id).padStart(3, "0");
        const name = NUM_TO_NAME[id] || (d.properties && d.properties.name) || "Unknown";
        const n = countByNum[id] || 0;
        const [x, y] = d3.pointer(event, container);
        tooltip
          .style("left", (x + 12) + "px")
          .style("top", (y + 12) + "px")
          .style("opacity", 1)
          .html(`<strong>${name}</strong><br>${n} paper${n === 1 ? "" : "s"}`);
        d3.select(this).attr("stroke", "#111").attr("stroke-width", 1.2);
      })
      .on("mouseleave", function () {
        tooltip.style("opacity", 0);
        d3.select(this).attr("stroke", "#fff").attr("stroke-width", 0.5);
      });

    drawLegend(svg, width, height, color, maxCount);
  }

  function drawLegend(svg, width, height, color, maxCount) {
    const legendW = 220, legendH = 10;
    const x = width - legendW - 20;
    const y = height - 30;

    const defs = svg.append("defs");
    const grad = defs.append("linearGradient")
      .attr("id", "citation-map-grad")
      .attr("x1", "0%").attr("x2", "100%");
    d3.range(0, 1.01, 0.1).forEach(t => {
      grad.append("stop")
        .attr("offset", (t * 100) + "%")
        .attr("stop-color", color(t * Math.log(maxCount + 1)));
    });

    const g = svg.append("g").attr("transform", `translate(${x},${y})`);
    g.append("rect")
      .attr("width", legendW).attr("height", legendH)
      .attr("fill", "url(#citation-map-grad)")
      .attr("stroke", "#94a3b8").attr("stroke-width", 0.5);
    g.append("text").attr("x", 0).attr("y", -4)
      .attr("font-size", 11).attr("fill", "#475569")
      .text("1");
    g.append("text").attr("x", legendW).attr("y", -4)
      .attr("text-anchor", "end")
      .attr("font-size", 11).attr("fill", "#475569")
      .text(maxCount);
    g.append("text").attr("x", legendW / 2).attr("y", -4)
      .attr("text-anchor", "middle")
      .attr("font-size", 11).attr("fill", "#475569")
      .text("papers per country");
  }

  render().catch(err => {
    console.error("citation-map render failed", err);
    container.innerHTML = '<p class="citation-map-empty">地図の読み込みに失敗しました</p>';
  });
})();
