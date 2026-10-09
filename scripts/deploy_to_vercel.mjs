import crypto from 'crypto';
import fs from 'fs';
import path from 'path';

const TOKEN = process.env.VERCEL_TOKEN || process.env.TOKEN || '';
const TEAM_ID = process.env.VERCEL_TEAM_ID || 'team_7460AU5lRh50DQIzK8Q6c5e7';
const PROJECT_NAME = 'terra07-heat-risk';
const PROJECT_ID = process.env.VERCEL_PROJECT_ID || 'prj_2FcGlgUN21Bi2CN1FuYQbhqIfIUf';

// Collect files to deploy
function getFilesRecursive(dir, base = '') {
  let results = [];
  if (!fs.existsSync(dir)) return results;
  const items = fs.readdirSync(dir, { withFileTypes: true });
  for (const item of items) {
    if (item.name === '__pycache__' || item.name.endsWith('.pyc') || item.name === '.git') continue;
    const fullPath = path.join(dir, item.name);
    const relPath = base ? `${base}/${item.name}` : item.name;
    if (item.isDirectory()) {
      results.push(...getFilesRecursive(fullPath, relPath));
    } else {
      const buffer = fs.readFileSync(fullPath);
      const sha = crypto.createHash('sha1').update(buffer).digest('hex');
      results.push({
        file: relPath.replace(/\\/g, '/'),
        path: fullPath,
        size: buffer.length,
        sha,
        buffer
      });
    }
  }
  return results;
}

async function uploadFile(fileEntry) {
  const res = await fetch(`https://api.vercel.com/v2/files?teamId=${TEAM_ID}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type': 'application/octet-stream',
      'x-vercel-digest': fileEntry.sha
    },
    body: fileEntry.buffer
  });

  if (!res.ok && res.status !== 409) {
    const err = await res.text();
    console.error(`Failed uploading ${fileEntry.file}:`, err);
    throw new Error(err);
  }
}

async function main() {
  console.log('====================================================');
  console.log('🚀 DEPLOYING TERRA07 HEAT-RISK TO VERCEL');
  console.log('====================================================\n');

  const files = [];

  // 1. Root configuration & entrypoints
  const singleFiles = ['vercel.json', 'index.html', '.vercelignore'];
  for (const f of singleFiles) {
    if (fs.existsSync(f)) {
      const buffer = fs.readFileSync(f);
      const sha = crypto.createHash('sha1').update(buffer).digest('hex');
      files.push({ file: f, path: f, size: buffer.length, sha, buffer });
    }
  }

  // 2. Directories
  const dirs = ['api', 'backend', 'engine', 'frontend', 'data', 'reports'];
  for (const d of dirs) {
    files.push(...getFilesRecursive(d, d));
  }

  console.log(`Found ${files.length} project files to deploy.`);
  let uploadedCount = 0;
  for (const f of files) {
    await uploadFile(f);
    uploadedCount++;
    if (uploadedCount % 10 === 0 || uploadedCount === files.length) {
      process.stdout.write(`Cached/Uploaded ${uploadedCount}/${files.length} files...\r`);
    }
  }
  console.log(`\nAll ${files.length} files successfully verified/uploaded.`);

  console.log('\nCreating production deployment on Vercel...');
  const deployPayload = {
    name: PROJECT_NAME,
    project: PROJECT_ID,
    target: 'production',
    files: files.map(f => ({
      file: f.file,
      sha: f.sha,
      size: f.size
    }))
  };

  const deployRes = await fetch(`https://api.vercel.com/v13/deployments?teamId=${TEAM_ID}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(deployPayload)
  });

  const deployData = await deployRes.json();
  if (!deployRes.ok) {
    console.error('Deployment creation failed:', JSON.stringify(deployData, null, 2));
    process.exit(1);
  }

  console.log(`\nDeployment triggered!`);
  console.log(`Deployment ID: ${deployData.id}`);
  console.log(`Deployment URL: https://${deployData.url}`);
  console.log(`Inspector: https://vercel.com/${TEAM_ID}/${PROJECT_NAME}/${deployData.id}`);
  console.log('Waiting for build to complete...\n');

  let ready = false;
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 3000));
    const checkRes = await fetch(`https://api.vercel.com/v13/deployments/${deployData.id}?teamId=${TEAM_ID}`, {
      headers: { 'Authorization': `Bearer ${TOKEN}` }
    });
    const checkData = await checkRes.json();
    process.stdout.write(`Status [check ${i + 1}]: ${checkData.readyState}...\r`);

    if (checkData.readyState === 'READY') {
      ready = true;
      console.log(`\n\n🎉 SUCCESS! Deployment is LIVE and READY!`);
      console.log(`Production URL: https://${checkData.url}`);
      if (checkData.alias && checkData.alias.length > 0) {
        console.log(`Aliases:`);
        checkData.alias.forEach(a => console.log(`👉 https://${a}`));
      }
      break;
    }

    if (checkData.readyState === 'ERROR') {
      console.error(`\n❌ Deployment ERROR:`, checkData);
      process.exit(1);
    }
  }

  if (!ready) {
    console.log(`\nDeployment still building in background. Check status at: https://vercel.com/${TEAM_ID}/${PROJECT_NAME}/${deployData.id}`);
  }
}

main().catch(console.error);
