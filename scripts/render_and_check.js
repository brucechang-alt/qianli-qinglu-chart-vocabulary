#!/usr/bin/env node
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const chrome = process.env.CHROME_PATH || undefined;
const qaDir = path.resolve(process.env.QA_OUTPUT_DIR || path.join(root, 'qa'));
fs.mkdirSync(qaDir, {recursive:true});
const mime = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.md':'text/markdown; charset=utf-8'};

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const clean = decodeURIComponent(req.url.split('?')[0]);
      if (clean === '/favicon.ico') { res.writeHead(204); res.end(); return; }
      const candidate = path.resolve(root, '.' + (clean === '/' ? '/index.html' : clean));
      if (!candidate.startsWith(root + path.sep) || !fs.existsSync(candidate) || fs.statSync(candidate).isDirectory()) {
        res.writeHead(404); res.end('Not found'); return;
      }
      res.writeHead(200, {'content-type': mime[path.extname(candidate).toLowerCase()] || 'application/octet-stream'});
      fs.createReadStream(candidate).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

(async () => {
  const server = await startServer();
  const port = server.address().port;
  const browser = await chromium.launch({headless:true, ...(chrome ? {executablePath:chrome} : {})});
  const failures = [];
  const page = await browser.newPage({viewport:{width:1440,height:1000}, deviceScaleFactor:1});
  page.on('console', msg => { if (msg.type() === 'error') failures.push(`console: ${msg.text()}`); });
  page.on('requestfailed', req => failures.push(`request: ${req.url()} ${req.failure()?.errorText || ''}`));
  await page.goto(`http://127.0.0.1:${port}/`, {waitUntil:'networkidle'});
  await page.waitForFunction(() => document.querySelectorAll('.chart-card').length === 67);
  await page.waitForTimeout(1800);
  const desktop = await page.evaluate(() => ({
    cards: document.querySelectorAll('.chart-card').length,
    filters: document.querySelectorAll('#filters button').length,
    width: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
    brokenImages: [...document.images].filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src),
    title: document.title
  }));
  const svgFetch = await page.evaluate(async () => {
    const response = await fetch('charts/change/01-01.svg');
    const body = await response.text();
    return {status:response.status,type:response.headers.get('content-type'),length:body.length,start:body.slice(0,80)};
  });
  const svgPage = await browser.newPage({viewport:{width:720,height:380}});
  const svgResponse = await svgPage.goto(`http://127.0.0.1:${port}/charts/change/01-01.svg`, {waitUntil:'load'});
  const svgDirect = {status:svgResponse.status(), content:(await svgPage.content()).slice(0,800), metrics:await svgPage.evaluate(()=>({tag:document.documentElement.tagName,children:document.documentElement.children.length,bbox:document.documentElement.getBBox?document.documentElement.getBBox():null}))};
  await svgPage.screenshot({path:path.join(qaDir,'svg-direct.png')});
  const imageProbePage = await browser.newPage({viewport:{width:720,height:380}});
  await imageProbePage.setContent(`<img id="probe" src="http://127.0.0.1:${port}/charts/change/01-01.svg" style="width:360px;height:190px">`);
  await imageProbePage.waitForTimeout(1000);
  const imageProbe = await imageProbePage.$eval('#probe', img => ({complete:img.complete,naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight}));
  await imageProbePage.screenshot({path:path.join(qaDir,'svg-image-probe.png')});
  await page.screenshot({path:path.join(root,'assets','qianli-qinglu-preview.jpg'),type:'jpeg',quality:90});

  const poster = await browser.newPage({viewport:{width:2400,height:900}, deviceScaleFactor:1});
  poster.on('requestfailed', req => failures.push(`poster request: ${req.url()} ${req.failure()?.errorText || ''}`));
  await poster.goto(`http://127.0.0.1:${port}/src/qianli-qinglu-chart-vocabulary.html`, {waitUntil:'networkidle'});
  const posterMetrics = await poster.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    height: document.documentElement.scrollHeight,
    families: document.querySelectorAll('.family-panel').length,
    charts: document.querySelectorAll('.chart-shell svg').length,
    referenceWidth: document.querySelector('.art-reference img')?.naturalWidth || 0,
    referenceHeight: document.querySelector('.art-reference img')?.naturalHeight || 0,
    brokenImages: [...document.images].filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src)
  }));
  await poster.screenshot({path:path.join(root,'assets','qianli-qinglu-poster.png'),fullPage:true});

  const mobile = await browser.newPage({viewport:{width:390,height:844}, deviceScaleFactor:1});
  await mobile.goto(`http://127.0.0.1:${port}/`, {waitUntil:'networkidle'});
  await mobile.waitForFunction(() => document.querySelectorAll('.chart-card').length === 67);
  await mobile.waitForTimeout(1800);
  const mobileMetrics = await mobile.evaluate(() => ({width:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth,cards:document.querySelectorAll('.chart-card').length,brokenImages:[...document.images].filter(img=>!img.complete||img.naturalWidth===0).length}));
  await mobile.screenshot({path:path.join(qaDir,'mobile-page.png'),fullPage:false});

  await browser.close(); server.close();
  if (desktop.cards !== 67 || posterMetrics.families !== 9 || posterMetrics.charts !== 67) failures.push('chart or family count mismatch');
  if (desktop.width > desktop.viewport || mobileMetrics.width > mobileMetrics.viewport) failures.push('horizontal overflow detected');
  if (desktop.brokenImages.length || posterMetrics.brokenImages.length || mobileMetrics.brokenImages) failures.push('broken image detected');
  const result = {desktop, svgFetch, svgDirect, imageProbe, poster:posterMetrics, mobile:mobileMetrics, failures};
  fs.writeFileSync(path.join(root,'validation.json'), JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  if (failures.length) process.exit(1);
})().catch(err => { console.error(err); process.exit(1); });
