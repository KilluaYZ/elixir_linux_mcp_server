from query import get_query

# 初始化查询对象，参数为数据根目录和项目名称
# q = get_query("/srv/elixir-data", "linux")
# 标识符查询示例 - 查询特定版本中的标识符定义
# res = q.query("ident", "v4.10", "raw_spin_unlock_irq", "C")

# contents = {
#     "define": [],
#     "reference": [],
#     "document": []
# }

# for it in res[0]:
#     contents["define"].append(it.to_dict())

# for it in res[1]:
#     contents["reference"].append(it.to_dict())

# for it in res[2]:
#     contents["document"].append(it.to_dict())

# res1 = q.query("dir", "v4.10", "/arch")
# print(res1)


REPO_DIR="/home/ziyang/works/kernel/linux"
import git 
repo = git.Repo(REPO_DIR)
import os

# 检出特定版本
# repo.git.checkout("v4.10")
# try:
#     cres = repo.git.checkout("v4.22")
#     print(f"cres = {cres}")

#     # 获取当前commit的log信息
#     commit = repo.head.commit
#     print(f"Commit Hash: {commit.hexsha}")
#     print(f"Author: {commit.author.name} <{commit.author.email}>")
#     print(f"Date: {commit.authored_datetime}")
#     print(f"Message:\n{commit.message}")

#     # 获取该commit的父commit信息
#     for parent in commit.parents:
#         print(f"\nParent Commit: {parent.hexsha}")

# except Exception as e:
#     print(e)

def print_tree(path, prefix='') -> str:
    """打印目录树结构"""
    result = ""
    files = os.listdir(path)
    for i, file in enumerate(files):
        # 判断是否是最后一个文件/目录
        is_last = i == len(files) - 1
        # 当前层级的前缀
        result = prefix + ('└── ' if is_last else '├── ') + file
        full_path = os.path.join(path, file)
        if os.path.isdir(full_path):
            # 递归打印子目录，更新前缀
            result += f"\n{print_tree(full_path, prefix + ('    ' if is_last else '│   '))}"
        
    return result 

print(".")
print(print_tree(REPO_DIR))



