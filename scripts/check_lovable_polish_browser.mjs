import { createRequire } from 'node:module';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import assert from 'node:assert/strict';
import { readBundle, boardRows } from '../lovable/src/lib/dg/backend.ts';
const require = createRequire(resolve('frontend/package.json'));
const { chromium } = require('playwright');
const base = process.env.DG_LOVABLE_URL ?? 'http://127.0.0.1:8798';
const out = process.env.DG_EVIDENCE_DIR;
const sid = process.env.DG_SNAPSHOT_ID;
if (!out) throw Error('A new DG_EVIDENCE_DIR is required');
if (!sid || !/^[a-f0-9]{64}$/.test(sid)) throw Error('A valid DG_SNAPSHOT_ID is required');
mkdirSync(out, { recursive:false });
const rows=boardRows(readBundle(JSON.parse(readFileSync('lovable/public/data/dg-bundle.json','utf8'))));
const mine=rows.find(r=>r.on_roster && r.full_name==='C.J. Stroud') ?? rows.find(r=>r.on_roster);
const rival=rows.find(r=>r.population==='default' && r.position===mine.position && r.player_id!==mine.player_id);
const checks=[];const browser=await chromium.launch();
const record=(name,ok,detail='')=>{checks.push({name,ok,detail});console.log(`${ok?'PASS':'FAIL'} ${name} ${detail}`);};
async function scenario(name,fn){try{await fn();record(name,true);}catch(e){record(name,false,String(e));}}
try {
 for(const width of [1440,390,320]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await scenario(`${width} roster and identity`,async()=>{
   await page.goto(base+'/',{waitUntil:'networkidle'});
   await page.getByRole('button',{name:new RegExp(mine.full_name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).first().waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   const loaded=await page.locator('main img').evaluateAll(imgs=>imgs.filter(i=>i.getBoundingClientRect().width>0&&i.getBoundingClientRect().top<innerHeight).every(i=>i.complete&&i.naturalWidth>0));assert.ok(loaded);
   await page.screenshot({path:join(out,`${width}-roster.png`)});
  });
  await scenario(`${width} keyboard search and current player`,async()=>{
   await page.keyboard.press('Control+k');
   const input=page.getByPlaceholder('Search by player name…');await input.waitFor();assert.ok(await input.evaluate(e=>document.activeElement===e));
   await page.keyboard.type(mine.full_name);await page.locator('.dg-search-dialog [cmdk-item]').first().waitFor();
   await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
   await page.locator('.dg-player-sheet[open]').waitFor();await page.locator('.dg-player-sheet').getByText('Current board reading',{exact:false}).waitFor();
   await page.screenshot({path:join(out,`${width}-player.png`)});await page.keyboard.press('Escape');await page.locator('.dg-player-sheet').waitFor({state:'hidden'});
  });
  await scenario(`${width} league filters preserve owned players`,async()=>{
   await page.goto(base+'/league',{waitUntil:'networkidle'});await page.getByText('274 rostered players.',{exact:false}).waitFor();
   await page.getByLabel('Roster',{exact:true}).selectOption('mine');await page.getByText('of 27 matching players',{exact:false}).waitFor();
   await page.getByLabel('Find a rostered player').fill(mine.full_name);await page.getByText('of 1 matching players',{exact:false}).waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   await page.screenshot({path:join(out,`${width}-league.png`)});
  });
  await scenario(`${width} choose two and compare`,async()=>{
   await page.goto(base+'/trades',{waitUntil:'networkidle'});
   await page.getByLabel('Find first player',{exact:true}).fill(mine.full_name);await page.getByRole('region',{name:'First player'}).locator('[cmdk-item]').first().click();
   await page.getByLabel('Find second player',{exact:true}).fill(rival.full_name);await page.getByRole('region',{name:'Second player'}).locator('[cmdk-item]').first().click();
   await page.getByRole('button',{name:'Compare players',exact:true}).click();await page.getByRole('region',{name:`${mine.full_name} compared with ${rival.full_name}`}).waitFor();
   const url=new URL(page.url());assert.equal(url.searchParams.get('player'),mine.player_id);assert.equal(url.searchParams.get('compare'),rival.player_id);
   await page.screenshot({path:join(out,`${width}-compare.png`)});await page.keyboard.press('Escape');
  });
  await scenario(`${width} real archive URL and current-board search`,async()=>{
   await page.goto(base+'/track-record?snapshot='+sid,{waitUntil:'networkidle'});await page.getByRole('heading',{name:'Football production',exact:true}).waitFor();
   assert.equal(new URL(page.url()).searchParams.get('snapshot'),sid);
   await page.getByRole('button',{name:'Find a player',exact:true}).click();await page.getByPlaceholder('Search by player name…').fill(mine.full_name);await page.locator('.dg-search-dialog [cmdk-item]').first().click();await page.locator('.dg-player-sheet[open]').waitFor();
   assert.equal(new URL(page.url()).searchParams.get('snapshot'),sid);await page.keyboard.press('Escape');assert.equal(new URL(page.url()).searchParams.get('snapshot'),sid);
   await page.reload({waitUntil:'networkidle'});await page.getByRole('heading',{name:'Football production',exact:true}).waitFor();assert.equal(new URL(page.url()).searchParams.get('snapshot'),sid);
   await page.screenshot({path:join(out,`${width}-track-record.png`)});
  });
  await scenario(`${width} invalid archive link refuses substitution`,async()=>{
   await page.goto(base+'/track-record?snapshot=bad-link',{waitUntil:'networkidle'});await page.getByText('This saved-reading link is invalid.',{exact:false}).waitFor();
   assert.equal(await page.getByRole('heading',{name:'Football production',exact:true}).count(),0);
   await page.getByRole('button',{name:'Open latest saved reading'}).click();await page.getByRole('heading',{name:'Football production',exact:true}).waitFor();
  });
  record(`${width} no application exceptions`,errors.length===0,errors.join(' | '));await context.close();
 }
} finally { await browser.close();writeFileSync(join(out,'results.json'),JSON.stringify(checks,null,2)); }
if(checks.some(c=>!c.ok))process.exitCode=1;
