module.exports = {
  apps: [
    {
      name: 'weorder',
      script: 'python',
      args: '-m uvicorn main:app --host 0.0.0.0 --port 9202',
      cwd: 'D:\\IISSERVER\\apps\\weorder',
      interpreter: 'none',
      env: {
        PORT: 9202
      },
      watch: false,
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      error_file: 'D:\\IISSERVER\\logs\\weorder\\error.log',
      out_file: 'D:\\IISSERVER\\logs\\weorder\\out.log',
      log_file: 'D:\\IISSERVER\\logs\\weorder\\combined.log',
      time: true
    }
  ]
};
