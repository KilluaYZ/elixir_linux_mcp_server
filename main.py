import subprocess
from mcp.server.fastmcp import FastMCP
import json
import os
import logging
import query
import git 
from build_resp import build_fail_resp, build_success_resp
from pathlib import Path
import time 

logger = logging.getLogger("linux_query_mcp")

settings = {
    "log_level": "DEBUG"
}

# 初始化mcp服务
mcp = FastMCP("linux-source-code-query", log_level="ERROR", settings=settings)
LXR_BASE_DIR=os.getenv("LXR_BASE_DIR")
REPO_DIR=os.getenv("REPO_DIR")
repo = git.Repo(REPO_DIR)

def get_query(project_name: str) -> query.Query:
    return query.get_query(LXR_BASE_DIR, project_name)


@mcp.tool()
async def query_ident(version: str, ident: str, family="C") -> str:
    """查询Linux内核代码标识符(identifiers),输入版本号,符号名,和符号类型,返回代码标识符查询结果
    
    Args:
        version (str): 要查询的项目的版本,例如v3.0,v4.10,v5.11等
        ident (str): 要查询的符号名称,例如raw_spin_unlock_irq等
        family (str): 要查询的符号类型. 只有两个值可选:B和C.如果是常规的代码标识符(identifiers)则传入"C". 如果是专门处理设备树(Device Tree)兼容性字符串(compatible strings)则传入"B"
    
    Returns:
        代码标识符(identifiers)查询结果,结果是一个json对象,其中分别有3个键值对,
        第1个键值对,键是define,值是一个list,表示这个这个符号被定义的信息,每一个元素是一个object,包含了路径(path),行号(line)和这个符号被定义时的类型(type),例如如果type为macro则说明是在宏中被定义,如果是member则说明是作为结构体成员被定义
        第2个键值对,键是reference,值是一个list,表示这个这个符号被引用的信息,每一个元素是一个object,包含了路径(path),行号(line)和这个符号被引用时的类型(type),这个类型一般都为null,可忽略
        第3个键值对,键是document,值是一个list,表示这个这个符号被文档注释的信息,每一个元素是一个object,包含了路径(path),行号(line)和这个符号被定义时的类型(type),这个类型一般都为null,可忽略
    """
    try:
        q = get_query("linux")
        res = q.query("ident", version, ident, family)
        contents = {
            "define": [],
            "reference": [],
            "document": []
        }

        for it in res[0]:
            contents["define"].append(it.to_dict())

        for it in res[1]:
            contents["reference"].append(it.to_dict())

        for it in res[2]:
            contents["document"].append(it.to_dict())

        return build_success_resp(data=contents, message=f"从{version}的Linux源码中获取标识符{ident}信息成功")
    
    except Exception as e:
        return build_fail_resp(message=f"从{version}的Linux源码中获取标识符{ident}信息失败.失败原因:{e}")

@mcp.tool()
async def get_tags() -> str:
    """查询Linux内核代码的所有tags,返回当前源码所有的tags
    
    Args:
        无
    
    Returns:
        返回一个json数组,其中每一项是一个标签名,例如[v1.0, v4.10, v6.6]
    """
    try:
        resp = []
        for tag in repo.tags:
            resp.append(tag.name)
        return build_success_resp(data=resp, message="查询Linux内核代码所有tags成功")
    except Exception as e:
        return build_fail_resp(message=f"查询Linux内核代码所有tags失败,失败原因:{e}")

@mcp.tool()
async def get_versions() -> str:
    """查询Linux内核代码的所有版本,返回Linux内核源码所有版本号
    
    Args:
        无
    
    Returns:
        返回一个json数组,其中每一项是一个版本名,例如[v1.0, v4.10, v6.6]
    """
    try:
        resp = []
        for tag in repo.tags:
            resp.append(tag.name)
        return build_success_resp(data=resp, message="查询Linux内核代码所有版本成功")
    except Exception as e:
        return build_fail_resp(message=f"查询Linux内核代码所有版本失败,失败原因:{e}")

@mcp.tool()
async def get_commit_info(commit_id: str):
    """获取Linux内核源码指定commit的信息,输入commit的hash id,返回该commit的相关信息

    Args:
        commit_id (str) : commit的id字符串  

    Returns:
        返回一个包含commit的信息json字符串,其中包含以下字段:
            commit_hash:当前commit的hash值
            author:当前commit的作者名
            author_email:当前commit的作者邮箱
            date:当前commit提交的日期
            message:当前commit提交时附加的信息
            parrent_commit_hash:当前commit的父commit的hash id
            diffs:当前commit相比于父commit的改变的列表,列表中每一个元素都是一个文件改变的信息,具体来说包含了以下信息
                diff_file:在本次commit中被修改的文件名
                diff_change_type:本次commit中,该文件被修改的类型,例如新增,修改,删除
                diff_change_content:本次commit中,该文件被修改的具体内容,其中'+'表示新增,'-'表示删除,与.diff文件解析方式类似
    """
    try:
        repo.git.checkout(commit_id)

        # 获取当前commit的log信息
        commit = repo.head.commit
        resp = {
            "commit_hash": commit.hexsha,
            "author": commit.author.name,
            "author_email": commit.author.email,
            "date": commit.authored_datetime,
            "message": commit.message.strip(),
            "parrent_commit_hash": [],
            "diffs": []
        }

        # 获取该commit的父commit信息
        for parent in commit.parents:
            resp['parrent_commit_hash'].append(parent.hexsha)
        
        # 获取该commit与父commit的差异
        if len(commit.parents) > 0:
            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)
        else:
            # 初始commit没有父节点
            diffs = commit.diff(git.NULL_TREE, create_patch=True)
        
        # 展示每个修改的文件和diff
        for diff in diffs:
            diff_tmp = {}
            diff_tmp["diff_file"] = diff.a_path if diff.a_path else diff.b_path
            diff_tmp["diff_change_type"] = diff.change_type
            if hasattr(diff, 'diff'):
                diff_tmp["diff_change_content"] = diff.diff.decode('utf-8') if isinstance(diff.diff, bytes) else diff.diff
            resp["diffs"].append(diff_tmp)

        return build_success_resp(data=resp, message=f"查询Linux内核源码id为{commit_id}的commit成功")
    except Exception as e:
        return build_fail_resp(message=f"查询Linux内核源码id为{commit_id}的commit失败,失败原因:{e}")


def dir_to_dict(path):
    """将目录结构转换为嵌套字典"""
    path = Path(path)
    if not path.exists():
        return None
    
    info = {
        'name': path.name,
        'type': 'directory',
        'path': str(path.resolve()),
        'size': path.stat().st_size,
        "create_time": time.ctime(path.stat().st_ctime),
        'children': []
    }
    
    for item in path.iterdir():
        if item.is_dir():
            info['children'].append(dir_to_dict(item))
        else:
            info['children'].append({
                "name": item.name,
                "type": "file",
                "path": str(item.resolve()),
                "size": item.stat().st_size,
                "create_time": time.ctime(item.stat().st_ctime),
                "last_monify_time": time.ctime(item.stat().st_mtime),
                "last_access_time": time.ctime(item.stat().st_atime),
            })
    
    return info

def execute_tree_command(path: str, recursive=False):
    """
    执行系统tree命令并返回输出
    
    参数:
        path (str): 要显示树结构的目录路径,默认为当前目录
        
    返回:
        str: tree命令的输出结果
    """
    cmd = []
    if recursive:
        cmd = ['tree', '-h' ,'-n', '-F', path]
    else:
        cmd = ['tree', '-h' ,'-n', '-F', '-L', '1', path]
    # 执行tree命令并捕获输出
    result = subprocess.run(cmd, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True)
    
    if result.returncode == 0:
        return result.stdout
    else:
        raise RuntimeError(f"执行tree命令出错: {result.stderr}")

@mcp.tool()
async def list_dir(version: str, path: str, detail = False, recursive=False) -> str:
    """展示Linux内核源码中某一个目录的内容,输入内核版本号或commit id,要展示的目录相对Linux内核源码根目录的路径,返回该目录中的内容信息

    Args:
        version (str) : 要查看的Linux内核版本,可以是一个具体的版本号,如v4.10,也可以是一个commit的hash id
        path (str) : 要查看的Linux内核源码中的目录路径,这个路径是相对于内核源码根目录的路径,例如: /arch, /drivers/gpu/
        detail (bool) : 是否展示更详细的信息,如果为True,那么该函数就会尽可能详细地返回查询结果,这可能会非常大。如果是False,则函数会返回较为精简的结果,默认为False
        recursive (bool) : 是否递归地展示待查询目录的内容,如果是True,那么函数就会递归地返回该目录所有的子文件和子目录。如果是False,那么函数就只会返回该目录下的子文件和子目录,不会再进行递归查找

    Returns:
        如果detail == False,则返回一个由tree命令生成的字符串来展示目录结构

        如果detail == True,则返回一个json字符串,其中包含了以下字段:
            name : 待查找的项目的名称
            type : 待查找的项目的类型
                    directory -> 目录
                    file -> 文件
            path : 待查找的项目的绝对路径
            size : 待查找的项目的大小(bytes)
            create : 待查找的项目的创建时间
            last_monify_time : 待查找的项目最近一次修改时间
            last_access_time : 待查找的项目最近一次被访问时间
            children : 待查找的项目如果是一个目录的话,这里会存放该目录下的所有子项目
    """
    try:
        repo.git.checkout(version)
        abs_path = Path(f"{REPO_DIR}/{path}")
        if not abs_path.is_dir():
            raise RuntimeError(f"目录{abs_path}不存在")
        
        if detail:
            info = {
                'name': abs_path.name,
                'type': 'directory',
                'path': str(abs_path.resolve()),
                'size': abs_path.stat().st_size,
                "create_time": time.ctime(abs_path.stat().st_ctime),
                'children': [] 
            }

            if recursive:
                info = dir_to_dict(abs_path)
            else:
                for item in abs_path.iterdir():
                    if item.is_file():
                        info['children'].append({
                            "name": item.name,
                            "type": "file",
                            "path": str(item.resolve()),
                            "size": item.stat().st_size,
                            "create_time": time.ctime(item.stat().st_ctime),
                            "last_monify_time": time.ctime(item.stat().st_mtime),
                            "last_access_time": time.ctime(item.stat().st_atime),
                        })
                    elif item.is_dir():
                        info['children'].append({
                            "name": item.name,
                            "type": "directory",
                            "path": str(item.resolve()),
                            "create_time": time.ctime(item.stat().st_ctime),
                        })
            return build_success_resp(data=info, message=f"展示目录{path}内容成功")

        else:
            info = execute_tree_command(path=str(abs_path.resolve()),recursive=recursive)
            return f"{path}的目录结构如下：\n{info}"

    except FileNotFoundError:
        return build_fail_resp(message=f"展示目录{path}内容失败,失败原因: 系统未安装tree命令,请先安装tree工具")
    
    except Exception as e:
        return build_fail_resp(message=f"展示目录{path}内容失败,失败原因:{e}")

@mcp.tool()
async def get_file_meta_info(version: str, path: str):
    """获取Linux内核源码中指定文件的元数据
    
    Args:
        version (str) : 要查看的Linux内核版本,可以是一个具体的版本号,如v4.10,也可以是一个commit的hash id
        path (str) : 要查看的Linux内核源码中某个文件的路径,这个路径是相对于内核源码根目录的路径,例如 /drivers/gpu/drm/amd/amdgpu/aldebaran_reg_init.c

    Returns:
        返回该文件的元数据,包含以下信息:
            name : 文件的名称
            type : 文件的类型
                    directory -> 目录
                    file -> 文件
            path : 文件的绝对路径
            size : 文件的大小(bytes)
            create : 文件的创建时间
            last_monify_time : 文件最近一次修改时间
            last_access_time : 文件最近一次被访问时间
    """
    try:
        repo.git.checkout(version)
        abs_path = Path(f"{REPO_DIR}/{path}")
        if not abs_path.exists():
            raise RuntimeError(f"文件{abs_path}不存在")

        if not abs_path.is_file():
            raise RuntimeError(f"{abs_path}不是一个文件")
        
        info = {
            'name': abs_path.name,
            'type': 'file',
            'path': str(abs_path.resolve()),
            'size': abs_path.stat().st_size,
            "create_time": time.ctime(abs_path.stat().st_ctime),
            "last_monify_time": time.ctime(abs_path.stat().st_mtime),
            "last_access_time": time.ctime(abs_path.stat().st_atime),
        }

        return build_success_resp(data=info, message=f"获取文件{path}元信息成功")

    except Exception as e:
        return build_fail_resp(message=f"获取文件{path}元信息失败,失败原因:{e}")

@mcp.tool()
async def get_file_content(version: str, path: str) -> str:
    """获取Linux内核源码中指定文件的内容
    
    Args:
        version (str) : 要查看的Linux内核版本,可以是一个具体的版本号,如v4.10,也可以是一个commit的hash id
        path (str) : 要查看的Linux内核源码文件的路径,这个路径是相对于内核源码根目录的路径,例如 /drivers/gpu/drm/amd/amdgpu/aldebaran_reg_init.c

    Returns:
        返回该文件的内容
    """
    try:
        repo.git.checkout(version)
        abs_path = Path(f"{REPO_DIR}/{path}")
        if not abs_path.exists():
            raise RuntimeError(f"文件{abs_path}不存在")

        if not abs_path.is_file():
            raise RuntimeError(f"{abs_path}不是一个文件")
        
        info = abs_path.read_text()

        # return build_success_resp(data=info, message=f"获取文件{path}内容成功")
        return f"文件{path}的内容如下：{info}"

    except Exception as e:
        return build_fail_resp(message=f"获取文件{path}内容失败,失败原因:{e}")

@mcp.tool()
async def check_if_file_exist(version: str, path: str):
    """查看Linux内核源码中指定文件是否存在
    
    Args:
        version (str) : 要查看的Linux内核版本,可以是一个具体的版本号,如v4.10,也可以是一个commit的hash id
        path (str) : 要查看的Linux内核源码文件的路径,这个路径是相对于内核源码根目录的路径,例如 /drivers/gpu/drm/amd/amdgpu/aldebaran_reg_init.c

    Returns:
        返回该文件是否存在的信息
    """
    try:
        repo.git.checkout(version)
        abs_path = Path(f"{REPO_DIR}/{path}")
        message = ""
        result = False
        if not abs_path.is_file():
            message = f"文件{path}不存在"
        else:
            result = True
            message = f"文件{path}存在" 
        
        return build_success_resp(data=result, message=message)

    except Exception as e:
        return build_fail_resp(message=f"查询文件{path}失败,失败原因:{e}")

@mcp.tool()
async def check_if_directory_exist(version: str, path: str):
    """查看Linux内核源码中指定目录是否存在
    
    Args:
        version (str) : 要查看的Linux内核版本,可以是一个具体的版本号,如v4.10,也可以是一个commit的hash id
        path (str) : 要查看的Linux内核源码目录的路径,这个路径是相对于内核源码根目录的路径,例如 /drivers/gpu/drm/amd/amdgpu/

    Returns:
        返回该目录是否存在的信息
    """
    try:
        repo.git.checkout(version)
        abs_path = Path(f"{REPO_DIR}/{path}")
        message = ""
        result = False
        if not abs_path.is_dir():
            message = f"目录{path}不存在"
        else:
            result = True
            message = f"目录{path}存在" 
        
        return build_success_resp(data=result, message=message)

    except Exception as e:
        return build_fail_resp(message=f"查询目录{path}失败,失败原因:{e}")

@mcp.tool()
async def check_if_commit_exist(commit_id: str):
    """查看Linux内核源码中指定commit是否存在
    
    Args:
        commit_id (str) : 要查看的Linux内核源码的commit id,可以是一个具体的版本号,如v4.10,也可以是一个commit的hash id

    Returns:
        返回该commit是否存在的信息
    """
    message = f"id为{commit_id}的commit存在"
    result = True
    try:
        repo.git.checkout(commit_id)
    except Exception as e:
        message = f"id为{commit_id}的commit不存在"
        result = False
    return build_success_resp(data=result, message=message)

@mcp.tool()
async def check_if_version_exist(version: str):
    """查看Linux内核源码中指定版本是否存在
    
    Args:
        version (str) : 要查看的Linux内核源码的指定版本,可以是一个具体的版本号,如v4.10

    Returns:
        返回该版本是否存在的信息
    """
    message = f"Linux内核源码版本{version}存在"
    result = True
    try:
        repo.git.checkout(version)
    except Exception as e:
        message = f"Linux内核源码版本{version}不存在"
        result = False
    return build_success_resp(data=result, message=message)

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
