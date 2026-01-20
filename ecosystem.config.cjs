/**
 * PM2 Ecosystem Configuration - WeOrder
 * ======================================
 * Production: Run from deploy/ folder on port 9203
 * 
 * Usage:
 *   pm2 start ecosystem.config.cjs
 *   pm2 restart weorder
 *   pm2 logs weorder
 * 
 * Note: This file is for reference. 
 *       Production uses D:\Server\ecosystem.config.js (central config)
 */
module.exports = {
  apps: [
    {
      name: 'weorder',
      script: 'python',
      args: '-m uvicorn main:app --host 0.0.0.0 --port 9203',
      cwd: 'D:\\Server\\deploy\\weorder',
      interpreter: 'none',
      env: {
        PORT: 9203,
        APP_PORT: 9203
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      error_file: 'D:\\Server\\logs\\weorder\\pm2-error.log',
      out_file: 'D:\\Server\\logs\\weorder\\pm2-out.log',
      log_file: 'D:\\Server\\logs\\weorder\\pm2-combined.log',
      time: true
    }
  ]
};
