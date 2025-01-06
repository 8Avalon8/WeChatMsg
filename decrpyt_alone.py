import os
import json
from app.decrypt import get_wx_info, decrypt
from app.DataBase.merge import merge_databases, merge_MediaMSG_databases
from app.config import DB_DIR

def load_version_list():
    """加载版本配置文件"""
    # app/data/version_list.json
    version_file = "./app/resources/data/version_list.json"
    if not os.path.exists(version_file):
        raise FileNotFoundError(f"版本配置文件不存在: {version_file}")
        
    with open(version_file, "r", encoding="utf-8") as f:
        version_list = json.load(f)
    return version_list

def decrypt_database():
    # 1. 获取微信版本和密钥信息
    try:
        VERSION_LIST = load_version_list()
    except Exception as e:
        print(f"加载版本配置文件失败: {str(e)}")
        return
        
    result = get_wx_info.get_info(VERSION_LIST)
    
    # 处理错误情况
    if isinstance(result, list):
        if result[0] == -1:
            print("请先登录微信")
            return
        elif result[0] == -2:
            print(f"微信版本不匹配，当前版本: {result[1]}")
            print("支持的版本列表:")
            for ver in VERSION_LIST.keys():
                print(f"- {ver}")
            return
        elif result[0] == -3:
            print("WeChat WeChatWin.dll Not Found") 
            return
    elif isinstance(result, str):
        print(f"当前微信版本 {result} 不受支持")
        print("支持的版本列表:")
        for ver in VERSION_LIST.keys():
            print(f"- {ver}")
        return
    
    # 确保result是字典类型
    result = result[0]
    if not isinstance(result, dict):
        print("获取微信信息失败")
        return
        
    key = result.get('key')
    wx_dir = result.get('filePath')
    
    if not key or key == "None":
        print("获取密钥失败")
        return
        
    if not wx_dir or not os.path.exists(wx_dir):
        print(f"微信数据目录不存在: {wx_dir}")
        return
        
    # 2. 解密数据库文件
    os.makedirs(DB_DIR, exist_ok=True)
    tasks = []
    
    for root, dirs, files in os.walk(os.path.join(wx_dir, 'Msg')):
        for file in files:
            if file.endswith('.db'):
                if file == 'xInfo.db':
                    continue
                inpath = os.path.join(root, file)
                output_path = os.path.join(DB_DIR, file)
                tasks.append([key, inpath, output_path])
            else:
                try:
                    name, suffix = file.split('.')
                    if suffix.startswith('db_SQLITE'):
                        inpath = os.path.join(root, file)
                        output_path = os.path.join(DB_DIR, name + '.db')
                        tasks.append([key, inpath, output_path])
                except:
                    continue

    # 3. 执行解密
    success_count = 0
    for task in tasks:
        success, msg = decrypt.decrypt(*task)
        if success:
            success_count += 1
            print(f"解密成功: {os.path.basename(task[1])}")
        else:
            print(f"解密失败: {os.path.basename(task[1])} - {msg}")
    
    if success_count == 0:
        print("没有成功解密任何文件")
        return
        
    # 4. 合并数据库
    try:
        target_database = os.path.join(DB_DIR, 'MSG.db')
        source_databases = [os.path.join(DB_DIR, f"MSG{i}.db") for i in range(1, 50)]
        
        if os.path.exists(target_database):
            os.remove(target_database)
            
        import shutil
        shutil.copy2(os.path.join(DB_DIR, 'MSG0.db'), target_database)
        merge_databases(source_databases, target_database)
        
        # 5. 合并语音消息数据库
        target_database = os.path.join(DB_DIR, 'MediaMSG.db')
        if os.path.exists(target_database):
            os.remove(target_database)
            
        source_databases = [os.path.join(DB_DIR, f"MediaMSG{i}.db") for i in range(1, 50)]
        shutil.copy2(os.path.join(DB_DIR, 'MediaMSG0.db'), target_database)
        merge_MediaMSG_databases(source_databases, target_database)
        
        print("数据库合并完成!")
    except Exception as e:
        print(f"合并数据库时出错: {str(e)}")

if __name__ == "__main__":
    decrypt_database()
