const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

console.log('Starting AI Music Playlist Generator...');

// Check if the required Python packages are installed
const checkPackages = spawn('pip', ['list']);
let packagesOutput = '';

checkPackages.stdout.on('data', (data) => {
  packagesOutput += data.toString();
});

checkPackages.on('close', (code) => {
  const requiredPackages = ['flask', 'openai', 'python-dotenv', 'requests', 'spotipy'];
  const missingPackages = [];
  
  for (const pkg of requiredPackages) {
    if (!packagesOutput.includes(pkg)) {
      missingPackages.push(pkg);
    }
  }
  
  if (missingPackages.length > 0) {
    console.log(`Installing missing packages: ${missingPackages.join(', ')}`);
    const installPackages = spawn('pip', ['install', ...missingPackages]);
    
    installPackages.stdout.on('data', (data) => {
      console.log(`${data}`);
    });
    
    installPackages.stderr.on('data', (data) => {
      console.error(`${data}`);
    });
    
    installPackages.on('close', (code) => {
      console.log(`Package installation completed with code ${code}`);
      startPythonApp();
    });
  } else {
    startPythonApp();
  }
});

function startPythonApp() {
  // Start the Python Flask application
  const pythonProcess = spawn('python', ['app.py']);
  
  pythonProcess.stdout.on('data', (data) => {
    console.log(`${data}`);
  });
  
  pythonProcess.stderr.on('data', (data) => {
    console.error(`${data}`);
  });
  
  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
  });
  
  // Create a simple HTTP server to keep the Node.js process running
  // and to provide a health check endpoint
  const server = http.createServer((req, res) => {
    if (req.url === '/health') {
      res.writeHead(200);
      res.end('Application is running');
    } else {
      // Forward other requests to the Python app
      res.writeHead(302, { 'Location': `http://localhost:3000${req.url}` });
      res.end();
    }
  });
  
  server.listen(8080, () => {
    console.log('Node.js wrapper server running on port 8080');
    console.log('Forwarding requests to Python application on port 3000');
  });
}