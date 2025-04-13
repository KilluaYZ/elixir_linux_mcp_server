from mcp.server.fastmcp import FastMCP
import json
import os
import logging
import query
import git 
from build_resp import build_fail_resp, build_success_resp

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


@mcp.tool(name="查询Linux内核代码标识符(identifiers)", description="查询Linux内核代码标识符(identifiers),输入要查询的Linux版本,符号和类型,能够返回该符号的定义、引用位置")
async def query_ident(version: str, ident: str, family="C") -> str:
    """查询Linux内核代码标识符(identifiers)
    
    Args:
        version (str): 要查询的项目的版本,例如v3.0,v4.10,v5.11等
        ident (str): 要查询的符号名称,例如raw_spin_unlock_irq等
        family (str): 要查询的符号类型. 只有两个值可选：B和C。如果是常规的代码标识符(identifiers)则传入"C". 如果是专门处理设备树(Device Tree)兼容性字符串(compatible strings)则传入"B"
    
    Returns:
        代码标识符(identifiers)查询结果,结果是一个json对象，其中分别有3个键值对，
        第1个键值对，键是define，值是一个list，表示这个这个符号被定义的信息，每一个元素是一个object,包含了路径(path),行号(line)和这个符号被定义时的类型（type），例如如果type为macro则说明是在宏中被定义，如果是member则说明是作为结构体成员被定义
        第2个键值对，键是reference，值是一个list，表示这个这个符号被引用的信息，每一个元素是一个object,包含了路径(path),行号(line)和这个符号被引用时的类型（type），这个类型一般都为null，可忽略
        第3个键值对，键是document，值是一个list，表示这个这个符号被文档注释的信息，每一个元素是一个object,包含了路径(path),行号(line)和这个符号被定义时的类型（type），这个类型一般都为null，可忽略
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
        return build_fail_resp(message=f"从{version}的Linux源码中获取标识符{ident}信息失败。失败原因：{e}")

@mcp.tool(name="查询Linux内核代码的所有tags", description="查询Linux内核代码的所有tags，返回当前linux源码所有的tags")
async def get_tags() -> str:
    """查询Linux内核代码的所有tags
    
    Args:
        无
    
    Returns:
        返回一个json数组，其中每一项是一个标签名，例如[v1.0, v4.10, v6.6]
    """
    try:
        resp = []
        for tag in repo.tags:
            resp.append(tag.name)
        return build_success_resp(data=resp, message="查询Linux内核代码所有tags成功")
    except Exception as e:
        return build_fail_resp(message=f"查询Linux内核代码所有tags失败，失败原因：{e}")

@mcp.tool(name="查询Linux内核代码的所有版本", description="查询Linux内核代码的所有版本，返回当前linux源码所有的版本名称")
async def get_versions() -> str:
    """查询Linux内核代码的所有版本
    
    Args:
        无
    
    Returns:
        返回一个json数组，其中每一项是一个版本名，例如[v1.0, v4.10, v6.6]
    """
    try:
        resp = []
        for tag in repo.tags:
            resp.append(tag.name)
        return build_success_resp(data=resp, message="查询Linux内核代码所有版本成功")
    except Exception as e:
        return build_fail_resp(message=f"查询Linux内核代码所有版本失败，失败原因：{e}")

@mcp.tool(name="获取Linux内核源码指定commit的信息", description="获取Linux内核源码指定commit的信息，接受commit_id作为参数，返回一个包含commit的信息json字符串")
async def get_commit_info(commit_id: str):
    """获取Linux内核源码指定commit的信息

    Args:
        commit_id (str) : commit的id字符串  

    Returns:
        返回一个包含commit的信息json字符串，其中包含：
            commit_hash：当前commit的hash值
            author：当前commit的作者名
            author_email：当前commit的作者邮箱
            date：当前commit提交的日期
            message：当前commit提交时附加的信息
            parrent_commit_hash：当前commit的父commit的hash id
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
            "message": commit.message,
            "parrent_commit_hash": []
        }

        # 获取该commit的父commit信息
        for parent in commit.parents:
            resp['parrent_commit_hash'].append(parent.hexsha)
        
        return build_success_resp(data=resp, message=f"查询Linux内核源码id为{commit_id}的commit成功")
    except Exception as e:
        return build_fail_resp(message=f"查询Linux内核源码id为{commit_id}的commit失败，失败原因：{e}")




def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
