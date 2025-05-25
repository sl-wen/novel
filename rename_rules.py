import os
import json
import glob
import shutil
import tempfile
import time

def wait_for_file_unlock(file_path, max_retries=10, delay=2):
    for _ in range(max_retries):
        try:
            # 尝试打开文件进行写入测试
            with open(file_path, 'a'):
                return True
        except PermissionError:
            print(f'File {file_path} is locked, waiting...')
            time.sleep(delay)
    return False

def safe_copy(src, dst):
    try:
        if wait_for_file_unlock(src):
            shutil.copy2(src, dst)
            return True
        return False
    except Exception as e:
        print(f'Error copying {src} to {dst}: {str(e)}')
        return False

def safe_remove(file_path):
    try:
        if wait_for_file_unlock(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f'Error removing {file_path}: {str(e)}')
        return False

def safe_move(src, dst):
    try:
        if wait_for_file_unlock(src):
            shutil.move(src, dst)
            return True
        return False
    except Exception as e:
        print(f'Error moving {src} to {dst}: {str(e)}')
        return False

def safe_rename(src, dst):
    if os.path.exists(dst):
        try:
            # 如果目标文件已存在，先读取两个文件的内容进行比较
            with open(src, 'r', encoding='utf-8') as f1, open(dst, 'r', encoding='utf-8') as f2:
                content1 = json.load(f1)
                content2 = json.load(f2)
                if content1['name'] == content2['name']:
                    # 如果是相同的规则，删除源文件
                    safe_remove(src)
                    print(f'Removed duplicate file {src}')
                    return
                else:
                    # 如果是不同的规则，保留源文件并添加后缀
                    base, ext = os.path.splitext(dst)
                    i = 1
                    while os.path.exists(f'{base}_{i}{ext}'):
                        i += 1
                    if wait_for_file_unlock(src):
                        safe_move(src, f'{base}_{i}{ext}')
                        print(f'Renamed {src} to {os.path.basename(dst)}_{i}{ext} (different content)')
                    return
        except Exception as e:
            print(f'Error comparing files {src} and {dst}: {str(e)}')
            return

    if wait_for_file_unlock(src):
        safe_move(src, dst)
        print(f'Renamed {src} to {os.path.basename(dst)}')

def remove_temp_files(directory):
    # 等待5秒，让其他进程完成对文件的操作
    time.sleep(5)
    temp_files = glob.glob(os.path.join(directory, 'rule-temp-*.json'))
    for f in temp_files:
        if safe_remove(f):
            print(f'Successfully removed temporary file {f}')
        else:
            print(f'Failed to remove temporary file {f}')

# 创建临时目录
temp_dir = tempfile.mkdtemp()
target_dir = 'd:/source/novel/resources/rule/new'

try:
    # 获取所有规则文件
    files = glob.glob(os.path.join(target_dir, 'rule-*.json'))
    
    # 第一步：复制到临时目录
    temp_files = []
    for i, f in enumerate(files):
        if not f.startswith(os.path.join(target_dir, 'rule-temp-')):
            temp_name = f'rule-temp-{i:02d}.json'
            temp_path = os.path.join(temp_dir, temp_name)
            if safe_copy(f, temp_path):
                temp_files.append(temp_path)
    
    # 第二步：删除原始文件（不包括临时文件）
    for f in files:
        if not f.startswith(os.path.join(target_dir, 'rule-temp-')):
            safe_remove(f)
    
    # 第三步：根据ID重命名并移回原目录
    for f in temp_files:
        try:
            # 读取文件中的id
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                file_id = data['id']
            
            # 生成新文件名
            new_name = f'rule-{file_id:02d}.json'
            new_path = os.path.join(target_dir, new_name)
            
            # 安全重命名文件
            safe_rename(f, new_path)
        except Exception as e:
            print(f'Error processing {f}: {str(e)}')

finally:
    # 清理临时目录
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f'Error cleaning up temp directory: {str(e)}')
    
    # 清理目标目录中的临时文件
    remove_temp_files(target_dir)