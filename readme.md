
## 项目结构
new_interface
 |—— app
 |  |——config    # 通用配置文件
 |  |——fid       # fid 接口
 |  |——hdc       # hdc 接口
 |—— .env.example  # 环境变量文件 TODO
 |—— .gitignore
 |—— Dockerfile
 |—— main.py        # 主文件
 |—— README.md
 |—— requirements.txt
 |—— restart_app.sh # 服务启动脚本


## 项目启动 

 nohup python main.py > output.log 2>&1 &

## 验证是否成功

 ps aux | grep main.py


### bug 记录
 
  请求 /api/fid_checker 接口时, 报错：Part exceeded maximum size of 1024KB.  

  修复方法: 修改 package -》 starlette- formparsers.py    约 155 行  修改为：self.max_part_size = 10 * 1024 * 1024


 
