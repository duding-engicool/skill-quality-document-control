# -*- coding: utf-8 -*-
"""
质量文件管控技能 —— 产物生成脚本

输入：JSON（任务类型 + 企业专属信息 + 可选明细）
输出：纯文字 Markdown 产物（按任务类型装配对应模块）
容错：任意字段缺失均标「待企业补充」，不崩溃。

用法：
  python build_report.py input.json
  python build_report.py input.json -o output.md
  cat input.json | python build_report.py -
"""
import json
import sys
import os
import datetime


# ----------------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------------
def get(data, key, default="待企业补充"):
    """安全取值，空字符串/None 视为缺失。"""
    v = data.get(key, None)
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return default
    return v


def as_list(v):
    """统一成列表。"""
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return v
    return [v]


def h1(t):
    return f"\n# {t}\n"


def h2(t):
    return f"\n## {t}\n"


def table(headers, rows):
    """生成 Markdown 表格。rows 为二维列表；空单元格用「待企业补充」填。"""
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        cells = [(str(c).strip() if str(c).strip() != "" else "待企业补充") for c in r]
        # 补齐列数
        while len(cells) < len(headers):
            cells.append("待企业补充")
        out.append("| " + " | ".join(cells[:len(headers)]) + " |")
    return "\n".join(out) + "\n"


# ----------------------------------------------------------------------------
# 各模块生成器（嵌入文件管控核心规则，作为脚本内置模板）
# ----------------------------------------------------------------------------
def sec_numbering(d):
    """编号体系设计。"""
    cc = get(d, "company_code", "ABC")
    out = h2("一、文件编号体系")
    out += "\n**标准格式**：`[公司代号]-[体系代号]-[层级代号]-[顺序号]-[版本号]`\n"
    out += "示例：`%s-QMS-QP-001-A` → 公司代号 / 体系(QMS) / 程序文件(QP) / 流水001 / 版本A\n" % cc
    out += h2("层级代号")
    rows = [
        ["QM", "Quality Manual", "质量手册", "纲领性文件"],
        ["QP", "Quality Procedure", "程序文件", "过程管控、职责定义"],
        ["WI", "Work Instruction", "作业指导书", "操作步骤（SWI公司级/DWI部门级/FWI现场级/SOP设备）"],
        ["RF", "Record Form", "表单记录", "证据留存、可追溯"],
        ["TS", "Technical Specification", "技术规范", "产品/材料规格"],
        ["ST", "Standard", "企业标准", "内部标准"],
        ["CP", "Control Plan", "控制计划", "过程控制"],
        ["FMEA", "Failure Mode Analysis", "失效模式分析", "DFMEA/PFMEA"],
    ]
    out += table(["层级代号", "英文", "全称", "说明"], rows)
    out += h2("体系代号（示例）")
    rows = [
        ["QMS", "质量管理体系", "ISO9001"],
        ["IATF", "汽车质量管理体系", "IATF16949"],
        ["EMS", "环境管理体系", "ISO14001"],
        ["OHS", "职业健康安全", "ISO45001"],
        ["QM", "医疗器械质量", "ISO13485"],
        ["FSMS", "食品安全管理", "ISO22000"],
        ["ISMS", "信息安全管理", "ISO27001"],
    ]
    out += table(["体系代号", "体系名称", "适用标准"], rows)
    out += h2("版本号规则")
    rows = [
        ["重大修订（内容变化>30%）", "字母递增", "A → B"],
        ["一般修订（局部修改）", "数字递增", "1 → 2"],
        ["轻微修订（文字/排版修正）", "数字递增", "1 → 2"],
        ["草稿阶段（不外发）", "小数递增", "0.1 → 0.2"],
    ]
    out += table(["变更类型", "版本升级", "示例"], rows)
    out += h2("外来文件编号")
    rows = [
        ["国家标准", "GB-[标准号]-[年份]", "GB-T19001-2016"],
        ["行业标准", "[行业]-[标准号]", "IATF-16949-2016"],
        ["客户文件", "CUST-[客户代码]-[类型]-[序号]", "CUST-TOYOTA-DWG-001"],
        ["供应商文件", "SUPP-[供应商代码]-[类型]-[序号]", "SUPP-ABC-SPEC-01"],
        ["受控外来", "[公司代号]-EXT-[原编号]-[年份]-[版本]", "%s-EXT-GB19001-2016-A" % cc],
    ]
    out += table(["类型", "编号格式", "示例"], rows)
    out += "\n> 注意：作废编号永久保留不复用；新文件用新流水号。编号须唯一、合规、可读、可扩展。\n"
    return out


def sec_change(d):
    """变更管理支持。"""
    out = h2("一、文件变更分级标准")
    rows = [
        ["重大变更", "质量方针/组织架构/顾客核心要求/法规符合性", "7天内完成评审", "总经理/管代"],
        ["一般变更", "程序流程/职责权限/作业方法/参数调整", "15天内完成评审", "质量经理/部门主管"],
        ["轻微变更", "文字修正/排版/错别字/格式统一", "3天内完成", "部门负责人"],
    ]
    out += table(["级别", "定义标准", "处理时限", "审批层级"], rows)
    out += h2("二、变更申请单（要素）")
    items = [
        "申请人/部门、申请日期",
        "文件编号 + 名称 + 当前版本",
        "变更类型：□重大 □一般 □轻微",
        "变更原因（必填）",
        "变更内容对比（原文 / 修订后）",
        "影响评估：关联文件、培训、设备、记录是否需同步",
        "对产品质量 / 顾客 / 法规的影响",
        "申请人签字 + 相关部门会签 + 批准",
    ]
    out += "\n".join(["- " + i for i in items]) + "\n"
    out += h2("三、影响评估清单（评审时核对）")
    checks = [
        "质量手册是否需要同步修订",
        "相关程序文件/作业指导书是否需要修订",
        "表单记录格式是否需调整",
        "设备参数/工装是否需调整",
        "检验标准是否需更新",
        "人员培训计划是否需制定",
        "供应商/顾客是否需通知",
        "法规符合性是否受影响",
    ]
    out += "\n".join(["- [ ] " + c for c in checks]) + "\n"
    out += h2("四、实施与验证流程")
    out += (
        "变更申请 → 初步评估 → 评审会签 → 批准 → 修订文件 → 审核确认 → 批准发布"
        " → 收回旧版 → 发放新版 → 培训通知 → 实施执行 → 效果验证 → 关闭变更单\n"
    )
    out += "\n> 紧急变更：可先执行后补手续（口头/微信批准须留证据），24h内补齐书面、7天内闭环。\n"
    return out


def sec_matrix(d):
    """文件矩阵 / 受控清单。"""
    out = h2("一、文件四级架构")
    rows = [
        ["第一层", "QM 质量手册", "质量方针、目标、组织架构", "1本"],
        ["第二层", "QP 程序文件", "过程管控、职责定义", "20-30份"],
        ["第三层", "WI 作业指导书", "操作步骤、技术要求", "30-50份"],
        ["第四层", "RF 表单记录", "证据留存、可追溯", "50-100份"],
    ]
    out += table(["层级", "类型", "内容", "数量参考"], rows)
    files = as_list(d.get("files", []))
    if files:
        out += h2("二、用户文件清单（编号体检）")
        rows = []
        for f in files:
            if isinstance(f, dict):
                rows.append([str(f.get("name", "待企业补充")),
                             str(f.get("level", "待企业补充")),
                             str(f.get("code", "待企业补充")),
                             str(f.get("version", "待企业补充")),
                             str(f.get("clause", "—"))])
            else:
                rows.append([str(f), "待企业补充", "待企业补充", "待企业补充", "—"])
        out += table(["文件名称", "层级", "编号", "版本", "ISO条款"], rows)
        out += "\n> 检查：编号是否唯一/合规、层级代号是否正确、版本规则是否一致、作废编号是否复用。\n"
    else:
        out += h2("二、文件矩阵框架（建议）")
        out += (
            "基于行业生成四层级清单（参考 references/document-matrix.md 约80份模板）：\n"
            "- 制造业通用：QM 1 + QP 25 + WI 35 + RF 60\n"
            "- 汽车行业须增 APQP/PPAP/FMEA/控制计划\n"
            "- 食品行业须增 HACCP/清洁消毒规程\n"
            "- 医疗器械须增 GMP/验证文件\n"
            "- 小微企业可精简至 40-50 份\n"
        )
        out += "\n> 未提供企业文件清单，以上为框架建议；提供后我可据实做编号体检与补全。\n"
    out += h2("三、受控清单（运行要求）")
    out += (
        "- 文控员维护《受控文件清单》（永久保存），记录编号/名称/版本/生效日\n"
        "- 版本追踪表记录发布日、下次评审日、变更次数与摘要\n"
        "- 作废文件入《作废文件清单》，原件至少留存一份用于追溯\n"
    )
    return out


def sec_retention(d):
    """留存期限判定。"""
    pl = get(d, "product_lifecycle", "待企业补充（影响留存年限，如产品生命周期+3年）")
    out = h2("一、记录分类保存期限")
    rows = [
        ["战略管理类", "质量手册/管理评审报告/内审报告/纠正预防措施记录", "永久", "文控/质量部"],
        ["合同与顾客类", "合同及评审/顾客投诉/退货/顾客财产", "合同终止后10年或永久", "销售/品质"],
        ["产品实现类", "设计输入输出/FMEA/控制计划/批次追溯", "永久或产品生命周期+3年", "研发/生产/品质"],
        ["检验与试验类", "IQC/IPQC/FQC/OQC 记录/不合格品处理", "3年（不合格品永久）", "品质"],
        ["供应商类", "评估/审核/整改/合格名录", "合作终止后3年（名录永久）", "SQE"],
        ["设备与工装类", "台账/维修/履历", "设备报废后5年", "设备"],
        ["计量类", "台账/检定证书/期间核查", "器具报废后5年", "计量"],
        ["人力资源类", "培训记录/特殊作业证书", "永久/离职后5年", "人事"],
        ["文件管理类", "发放/回收/变更单/受控清单", "3年（变更单/清单永久）", "文控"],
        ["生产运营类", "生产计划/日报/流转卡/出入库", "1-3年", "生产/仓库"],
    ]
    out += table(["类别", "代表记录", "保存年限", "责任人"], rows)
    out += h2("二、法规最低要求（优先满足）")
    rows = [
        ["产品质量法", "产品检验记录", "2年"],
        ["合同法", "合同及附件", "合同终止后3年"],
        ["劳动合同法", "劳动合同/工资台账", "解除后2年"],
        ["IATF16949", "PPR/过程FMEA/控制计划", "零件停产+10年（或法规）"],
        ["ISO13485", "设计/生产/检验/投诉记录", "永久或产品生命周期+2年"],
        ["食品安全法", "原料/生产/检验/销售记录", "2年（召回5年）"],
    ]
    out += table(["法规", "相关记录", "保存年限"], rows)
    out += "\n> 原则：**法规优先**；顾客要求高于法规时以顾客为准；产品生命周期=%s\n" % pl
    out += h2("三、销毁要求")
    out += (
        "- 判定：保存期限已满、状态“待销毁”、无未决追溯/法律纠纷\n"
        "- 流程：到期提醒 → 部门申请 → 质量部审核 → 主管批准 → 实施销毁 → 登记 → 更新台账\n"
        "- 销毁须有监销人，记录必须保存；涉及法律纠纷立即停止销毁并延期\n"
    )
    return out


def sec_external(d):
    """外来文件受控指引。"""
    out = h2("一、外来文件分类与受控要求")
    rows = [
        ["法规文件", "产品质量法、安全生产法", "及时获取、版本跟踪"],
        ["国家标准", "GB/T 19001、GB/T 24001", "购买正式版本、及时更新"],
        ["行业标准", "IATF16949、ISO13485", "版本有效性确认"],
        ["客户文件", "图纸、规范、标准", "按客户要求受控管理"],
        ["供应商文件", "检验标准、规格书", "来料检验时同步受控"],
    ]
    out += table(["类型", "示例", "管理要求"], rows)
    out += h2("二、受控要点")
    out += (
        "- 质量部统一登记，建立《外来文件清单》\n"
        "- 发放前检查版本有效性，加盖“受控文件”章\n"
        "- 定期跟踪标准更新，及时获取新版本\n"
        "- 建议重新编号（如 %s-EXT-...）便于统一追溯，原件编号记入备注\n"
        % get(d, "company_code", "ABC")
    )
    return out


def sec_version(d):
    """版本与作废判断。"""
    out = h2("一、版本升级规则")
    rows = [
        ["重大修订（>30%）", "A→B（字母递增）", "回收所有旧版、记录变更摘要"],
        ["一般修订", "1→2（数字递增）", "更新受控清单"],
        ["轻微修订", "1→2（数字递增）", "局部更新"],
        ["草稿", "0.1→0.2", "内部使用，不外发"],
    ]
    out += table(["变更类型", "版本升级", "换版动作"], rows)
    out += h2("二、作废判定与处理")
    out += (
        "**判定条件**：新版本已发布 / 被其他文件替代 / 适用法规标准已更新 / 产品工艺淘汰 / 超保存期\n\n"
        "**处理流程**：确认新版本受控 → 填《文件作废申请》 → 审批（文控+质量部）→"
        " 原件盖“作废”红章 → 从使用场所回收 → 登记《作废文件清单》 → 归档或销毁\n\n"
        "> 作废文件不得与受控文件混放；建议至少留存一份原件用于审核追溯。\n"
    )
    return out


SECTIONS = {
    "numbering": sec_numbering,
    "change": sec_change,
    "matrix": sec_matrix,
    "retention": sec_retention,
    "external": sec_external,
    "version": sec_version,
    "obsolete": sec_version,
}

SECTION_TITLE = {
    "numbering": "文件编号体系设计",
    "change": "文件变更管理支持",
    "matrix": "文件矩阵 / 受控清单",
    "retention": "记录留存期限判定",
    "external": "外来文件受控指引",
    "version": "版本与作废判断",
    "obsolete": "版本与作废判断",
}


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def build(data):
    company = get(data, "company_code", "ABC")
    industry = get(data, "industry", "待企业补充")
    cust = get(data, "customer_requirements", "待企业补充")

    md = "# 质量文件管控产物\n"
    md += "\n> 生成时间：%s ｜ 本产物为规范模板，企业专属信息已标注「待企业补充」处需责任人确认。\n" % (
        datetime.date.today().isoformat())
    md += h2("基础信息")
    rows = [
        ["公司代号", company],
        ["行业 / 体系", industry],
        ["顾客特殊要求", cust],
    ]
    md += table(["项目", "内容"], rows)

    types = as_list(data.get("task_type", []))
    if isinstance(types, list) and types and isinstance(types[0], dict):
        types = [t.get("type", "") for t in types]
    if not types:
        types = ["numbering"]
    # 规范化
    norm = []
    for t in types:
        t = str(t).strip().lower()
        if t in SECTIONS:
            norm.append(t)
    if not norm:
        norm = ["numbering"]

    for i, t in enumerate(norm, 1):
        md += "\n---\n"
        md += h1("%d. %s" % (i, SECTION_TITLE.get(t, t)))
        md += SECTIONS[t](data)

    notes = get(data, "notes", "")
    if notes and notes != "待企业补充":
        md += "\n---\n" + h2("附加说明") + "\n" + notes + "\n"

    md += "\n---\n*本产物由质量文件管控技能生成，供企业结合实际情况裁剪使用。*\n"
    return md


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("用法: python build_report.py <input.json|-> [-o output.md]\n")
        sys.exit(1)
    src = sys.argv[1]
    out_path = None
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            out_path = sys.argv[idx + 1]

    # 读取 JSON
    try:
        if src == "-":
            raw = sys.stdin.read()
        else:
            with open(src, "r", encoding="utf-8") as f:
                raw = f.read()
        data = json.loads(raw)
    except Exception as e:
        sys.stderr.write("读取/解析输入失败: %s\n" % e)
        sys.exit(2)

    if not isinstance(data, dict):
        sys.stderr.write("输入 JSON 顶层必须是对象\n")
        sys.exit(3)

    md = build(data)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        sys.stderr.write("已生成: %s\n" % out_path)
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
