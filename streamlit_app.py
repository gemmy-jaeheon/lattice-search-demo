import streamlit as st
import requests

st.set_page_config(page_title="Lattice", page_icon="🔍", layout="wide")

API_URL = st.secrets["SUPABASE_API_URL"]
API_KEY = st.secrets["SUPABASE_ANON_KEY"]

# 별칭 → workspace_id 매핑 (테스트용)
WORKSPACE_ALIASES = {
    "cogp": "0aa2dc76-6301-4d1e-beff-919534c416c7",
    "bluepoint": "15524004-c36a-4433-9a23-148b0546da3d",
    "gp": "2620ff38-236f-4d19-90b7-38d3df03ff67",
    "gp2": "e27ce0c4-27ea-4756-96ed-68e960c0920e",
    "cogp2": "2c4f7966-4f6d-4a3a-8ca1-289c56e5b670",
    "cogp3": "95c3556c-d44a-4f3d-8068-94a69fe08c9f",
}

# 비밀번호 필요 워크스페이스
WORKSPACE_PASSWORDS = {
    "admin": "Gemmy1115*",
    "bluepoint": "Bluepoint07!",
}

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.workspace_alias = None
    st.session_state.workspace_id = None
    st.session_state.is_admin = False
    st.session_state.debug_mode = False
    st.session_state.messages = []


def login(alias: str, password: str = "") -> tuple[bool, str]:
    """별칭으로 로그인 시도. 반환: (성공여부, 에러메시지)"""
    alias = alias.strip().lower()

    # 비밀번호 필요 워크스페이스 확인
    if alias in WORKSPACE_PASSWORDS:
        if password != WORKSPACE_PASSWORDS[alias]:
            return False, "비밀번호가 틀렸습니다."

    if alias == "admin":
        st.session_state.logged_in = True
        st.session_state.workspace_alias = "admin"
        st.session_state.workspace_id = None
        st.session_state.is_admin = True
        return True, ""

    if alias in WORKSPACE_ALIASES:
        st.session_state.logged_in = True
        st.session_state.workspace_alias = alias
        st.session_state.workspace_id = WORKSPACE_ALIASES[alias]
        st.session_state.is_admin = False
        return True, ""

    return False, "존재하지 않는 워크스페이스입니다."


def logout():
    """로그아웃"""
    st.session_state.logged_in = False
    st.session_state.workspace_alias = None
    st.session_state.workspace_id = None
    st.session_state.is_admin = False
    st.session_state.messages = []


def call_chat_api(query: str) -> dict:
    """Chat API 호출 (검색 + LLM 요약)"""
    # API_URL에서 base URL 추출
    base_url = API_URL.rsplit("/", 1)[0]  # /functions/v1
    chat_url = f"{base_url}/chat"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    if not st.session_state.is_admin and st.session_state.workspace_id:
        headers["x-workspace-id"] = st.session_state.workspace_id

    response = requests.post(
        chat_url,
        headers=headers,
        json={"query": query},
        timeout=60,  # LLM 처리 시간 고려
    )
    return {"data": response.json(), "status": response.status_code}


def generate_single_company_summary(company: dict) -> str:
    """1개 기업에 대한 상세 서머리 생성"""
    name = company.get("name", "")
    industry = company.get("industry", "")
    region = company.get("region", "")
    round_val = company.get("round", "")
    stage = company.get("stage", "")
    ceo_name = company.get("ceo_name", "")
    summary_text = company.get("summary", "")
    technologies = company.get("technologies", "")
    pre_money = company.get("pre_money_valuation")

    lines = []

    # 1줄: 기본 정보
    intro_parts = []
    if industry:
        intro_parts.append(f"{industry} 분야")
    if round_val:
        intro_parts.append(f"{round_val.upper()} 단계")
    if region:
        intro_parts.append(f"{region} 소재")

    intro = ", ".join(intro_parts) if intro_parts else ""
    lines.append(f"**{name}**은(는) {intro} 기업입니다." if intro else f"**{name}**입니다.")

    # 2줄: 대표자 + 단계
    detail_parts = []
    if ceo_name:
        detail_parts.append(f"대표는 **{ceo_name}**")
    if stage:
        stage_map = {"discovery": "발굴", "review": "검토", "due_diligence": "실사", "investment": "투자", "portfolio": "포트폴리오"}
        detail_parts.append(f"현재 {stage_map.get(stage, stage)} 단계")
    if detail_parts:
        lines.append(", ".join(detail_parts) + "입니다.")

    # 3줄: 사업 요약
    if summary_text:
        lines.append(f"")
        lines.append(f"> {summary_text}")

    # 4줄: 기술스택
    if technologies:
        lines.append(f"")
        lines.append(f"**기술**: {technologies}")

    # 5줄: 밸류에이션
    if pre_money:
        val_str = f"{pre_money / 100_000_000:,.0f}억원" if pre_money >= 100_000_000 else f"{pre_money / 10_000:,.0f}만원"
        lines.append(f"**Pre-money**: {val_str}")

    return "\n".join(lines)


def generate_multi_company_summary(results: list, meta: dict) -> str:
    """2-3개 기업에 대한 요약 (각 1줄씩)"""
    reference_company = meta.get("reference_company")
    matched_conditions = meta.get("matched_conditions", {})
    count = len(results)

    lines = []

    # 헤더
    if reference_company:
        lines.append(f"**{reference_company}**와 유사한 {count}개 기업을 찾았습니다.")
    elif matched_conditions:
        cond_parts = []
        if matched_conditions.get("industry"):
            cond_parts.append(matched_conditions["industry"])
        if matched_conditions.get("region"):
            cond_parts.append(matched_conditions["region"])
        if matched_conditions.get("round"):
            cond_parts.append(matched_conditions["round"])
        if cond_parts:
            lines.append(f"{' '.join(cond_parts)} 조건에 맞는 {count}개 기업입니다.")
        else:
            lines.append(f"{count}개 기업을 찾았습니다.")
    else:
        lines.append(f"{count}개 기업을 찾았습니다.")

    lines.append("")

    # 각 기업 1줄씩
    for c in results:
        name = c.get("name", "")
        industry = c.get("industry", "")
        summary = c.get("summary", "")
        summary_short = summary[:60] + "..." if len(summary) > 60 else summary
        line = f"• **{name}**"
        if industry:
            line += f" ({industry})"
        if summary_short:
            line += f" - {summary_short}"
        lines.append(line)

    return "\n".join(lines)


def generate_summary(results: list, meta: dict) -> str:
    """검색 결과에 대한 자연어 서머리 생성 (개수에 비례)"""
    count = len(results)
    reference_company = meta.get("reference_company")
    matched_conditions = meta.get("matched_conditions", {})

    # 1개: 매우 상세
    if count == 1:
        return generate_single_company_summary(results[0])

    # 2-3개: 각 기업 1줄씩
    if count <= 3:
        return generate_multi_company_summary(results, meta)

    # 4-9개: 기업명 나열
    names = [r.get("name", "") for r in results[:5]]
    names_str = ", ".join(names)
    if count > 5:
        names_str += f" 외 {count - 5}개"

    if reference_company:
        return f"**{reference_company}**와 유사한 {count}개 기업을 찾았습니다: {names_str}"

    if matched_conditions:
        conditions_desc = []
        if matched_conditions.get("industry"):
            conditions_desc.append(matched_conditions["industry"])
        if matched_conditions.get("region"):
            conditions_desc.append(matched_conditions["region"])
        if matched_conditions.get("round"):
            conditions_desc.append(matched_conditions["round"])
        if conditions_desc:
            return f"{' '.join(conditions_desc)} 조건에 맞는 {count}개 기업입니다: {names_str}"

    return f"{count}개 기업을 찾았습니다: {names_str}"


# 컬럼 출처 매핑 (뷰 컬럼 → 원본 테이블/계산 방식)
COLUMN_SOURCES = {
    "high_risk": "risk_assessments → 5개 플래그 합산 ≥ 3",
    "risk_flags": "risk_assessments.has_*_issue (최신 분기)",
    "risk_executive": "risk_assessments.has_executive_issue",
    "risk_cashflow": "risk_assessments.has_cashflow_issue",
    "risk_capital_erosion": "risk_assessments.has_capital_erosion_issue",
    "risk_key_personnel": "risk_assessments.has_key_personnel_issue",
    "risk_competitor": "risk_assessments.has_competitor_issue",
    "report_status": "portfolio_reports.status (최신 분기)",
    "reexamine": "stage='dropped' AND (has_evaluation_completed OR has_pitching_completed)",
    "drop_reasons_contains": "investor_startups.drop_reasons (배열→텍스트 LIKE)",
    "fund_name": "investments → funds.name (최신 투자)",
    "is_capital_impaired": "portfolio_reports.total_equity < 0",
    "capital_impairment": "portfolio_reports.total_equity < 0",
    "has_evaluation_completed": "investment_evaluations.status IN ('completed', 'contract_signed')",
    "has_pitching_completed": "pitching_evaluations.is_completed = true",
    "industry": "investor_industries.name",
    "region": "investor_startups.state",
    "round": "workspaces.round",
    "stage": "investor_startups.investment_stage",
    "ceo_gender": "workspace_members.individual_id (주민번호 뒷자리)",
    "sourcing_channel": "investor_sourcing_channels.name",
    "sourcing_date_gte": "investor_startups.sourcing_date ≥",
    "sourcing_date_lte": "investor_startups.sourcing_date ≤",
    "round_gte": "workspaces.round (라운드 순서 비교)",
    "round_lte": "workspaces.round (라운드 순서 비교)",
    "pre_money_valuation_gte": "investments.pre_money_valuation ≥",
}


def get_condition_sources(conditions: dict) -> dict:
    """matched_conditions의 각 키에 대한 출처 반환"""
    if not conditions:
        return {}
    sources = {}
    for key in conditions.keys():
        if key in COLUMN_SOURCES:
            sources[key] = COLUMN_SOURCES[key]
        elif key.endswith("_gte") or key.endswith("_lte"):
            base_key = key[:-4]
            if base_key in COLUMN_SOURCES:
                sources[key] = COLUMN_SOURCES.get(key, f"{COLUMN_SOURCES[base_key]} (범위)")
    return sources


def format_matched_conditions(conditions: dict) -> str:
    """matched_conditions를 한글로 풀어서 표시"""
    if not conditions:
        return ""

    labels = []

    # 기본 필터
    if conditions.get("industry"):
        labels.append(f"산업: {conditions['industry']}")
    if conditions.get("region"):
        labels.append(f"지역: {conditions['region']}")
    if conditions.get("round"):
        labels.append(f"라운드: {conditions['round'].upper()}")
    if conditions.get("stage"):
        stage_map = {
            "discovery": "발굴", "review": "검토", "due_diligence": "실사",
            "management": "관리", "dropped": "탈락", "exit": "엑싯", "impaired": "손상"
        }
        labels.append(f"단계: {stage_map.get(conditions['stage'], conditions['stage'])}")
    if conditions.get("ceo_gender"):
        gender = "여성" if conditions["ceo_gender"] == "F" else "남성"
        labels.append(f"대표: {gender}")

    # 범위 필터
    if conditions.get("round_gte"):
        labels.append(f"시리즈{conditions['round_gte'].upper()} 이상")
    if conditions.get("round_lte"):
        labels.append(f"시리즈{conditions['round_lte'].upper()} 이하")
    if conditions.get("pre_money_valuation_gte"):
        val = conditions["pre_money_valuation_gte"] / 100_000_000
        labels.append(f"밸류에이션 {val:.0f}억 이상")
    if conditions.get("sourcing_date_gte"):
        labels.append(f"발굴일: {conditions['sourcing_date_gte']} 이후")
    if conditions.get("sourcing_date_lte"):
        labels.append(f"발굴일: {conditions['sourcing_date_lte']} 이전")

    # Phase 2 고급 필터
    if conditions.get("high_risk"):
        labels.append("🔴 고위험 (리스크 3개↑)")
    if conditions.get("risk_flags"):
        flag_map = {
            "cashflow": "현금흐름", "executive": "경영진",
            "capital_erosion": "자본잠식", "key_personnel": "핵심인력", "competitor": "경쟁사"
        }
        flags = [flag_map.get(f, f) for f in conditions["risk_flags"]]
        labels.append(f"리스크: {', '.join(flags)}")
    if conditions.get("report_status") == "in_progress":
        labels.append("📋 보고서 미제출")
    if conditions.get("report_status") == "completed":
        labels.append("📋 보고서 제출완료")
    if conditions.get("reexamine"):
        basis = conditions.get("reexamine_basis", "")
        if basis == "evaluation_or_pitching":
            labels.append("🔄 재검토 대상 (심사/피칭 후 탈락)")
        else:
            labels.append("🔄 재검토 대상")
    if conditions.get("drop_reasons_contains"):
        labels.append(f"탈락사유: '{conditions['drop_reasons_contains']}' 포함")
    if conditions.get("fund_name"):
        labels.append(f"펀드: {conditions['fund_name']}")
    if conditions.get("capital_impairment"):
        labels.append("🔴 자본잠식")

    return " · ".join(labels) if labels else str(conditions)


def render_startup_results(data: dict):
    """스타트업 검색 결과 렌더링"""
    meta = data.get("meta", {})
    results = data.get("results", [])
    matched_conditions = meta.get("matched_conditions", {})
    count = len(results)

    # 10개 미만이면 자연어 서머리 표시
    if count < 10:
        summary = generate_summary(results, meta)
        st.markdown(summary)
        st.markdown("---")

    st.markdown(f"**검색 결과** ({meta.get('total', len(results))}건) · `{meta.get('route_type', '-')}`")

    if matched_conditions:
        st.caption(f"적용 조건: {format_matched_conditions(matched_conditions)}")
    if meta.get("reference_company"):
        st.caption(f"참조 기업: {meta['reference_company']}")

    for company in results:
        # 뱃지 생성
        badges = []
        if company.get("is_capital_impaired"):
            badges.append("🔴 자본잠식")
        if company.get("has_exit"):
            badges.append("💰 엑싯")
        badge_str = " ".join(badges)

        title = f"**{company['name']}** - {company.get('industry', '-')}"
        if badge_str:
            title += f"  {badge_str}"

        with st.expander(title):
            # 기본 4컬럼
            cols = st.columns(4)
            cols[0].markdown(f"**대표:** {company.get('ceo_name', '-')}")
            cols[1].markdown(f"**지역:** {company.get('region', '-')}")
            cols[2].markdown(f"**라운드:** {company.get('round', '-')}")
            cols[3].markdown(f"**단계:** {company.get('stage', '-')}")

            # 동적 필드 (matched_conditions 기반)
            dynamic_fields = []
            if "capital_impairment" in matched_conditions:
                status = "자본잠식" if company.get("is_capital_impaired") else "자본잠식 아님"
                dynamic_fields.append(f"**자본상태:** {status}")
            if "ceo_gender" in matched_conditions:
                gender = {"F": "여성", "M": "남성"}.get(company.get("ceo_gender"), "-")
                dynamic_fields.append(f"**대표 성별:** {gender}")
            if "has_exit" in matched_conditions:
                exit_status = "O" if company.get("has_exit") else "X"
                dynamic_fields.append(f"**엑싯:** {exit_status}")
            if "sourcing_channel" in matched_conditions:
                dynamic_fields.append(f"**발굴채널:** {company.get('sourcing_channel', '-')}")

            if dynamic_fields:
                st.markdown(" · ".join(dynamic_fields))

            if company.get("investment_date"):
                st.caption(f"투자일: {company['investment_date']}")
            if company.get("summary"):
                st.markdown(company["summary"])
            if company.get("technologies"):
                st.markdown(f"**기술:** {company['technologies']}")
            if company.get("pre_money_valuation"):
                val = company["pre_money_valuation"]
                st.markdown(f"**Pre-money:** {val / 100_000_000:.0f}억원")


def render_analytics_results(data: dict):
    """통계 결과 렌더링"""
    meta = data.get("meta", {})
    st.markdown(f"**📊 통계 결과**")
    st.caption(meta.get("description", ""))

    if data.get("data"):
        st.dataframe(data["data"], use_container_width=True)
    else:
        st.info("집계 결과가 없습니다.")

    if data.get("clarification_options"):
        st.markdown("**선택지:** " + ", ".join(data["clarification_options"]))


def render_web_results(data: dict):
    """웹검색 결과 렌더링 (번호 형태 출처 표기)"""
    results = data.get("results", [])
    meta = data.get("meta", {})

    st.markdown(f"**🌐 웹 검색 결과** · `{meta.get('query', '')}`")

    if not results:
        st.info("검색 결과가 없습니다.")
        return

    # 번호 형태로 결과 표시
    for i, r in enumerate(results, 1):
        st.markdown(f"[{i}] **[{r.get('title', '')}]({r.get('link', '')})**")
        st.caption(r.get("snippet", ""))

    # 하단 출처 목록
    st.markdown("---")
    st.markdown("**출처:**")
    for i, r in enumerate(results, 1):
        st.markdown(f"[{i}] {r.get('link', '')}")


def format_krw(value):
    """숫자를 한국 원화 형식으로 포맷"""
    if value is None:
        return "-"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:,.0f}억원"
    elif abs(value) >= 10_000:
        return f"{value / 10_000:,.0f}만원"
    else:
        return f"{value:,.0f}원"


def render_financial_results(data: dict):
    """재무제표 결과 렌더링"""
    company = data.get("company", {})
    period = data.get("period", {})
    summary = data.get("summary", {})
    full = data.get("full", {})
    meta = data.get("meta", {})

    # 헤더
    st.markdown(f"**📈 {company.get('name', '')} 재무제표** · {period.get('year', '')}년 {period.get('quarter', '')}")

    if meta.get("is_capital_impaired"):
        st.warning("⚠️ 자본잠식 상태입니다")

    # 요약 (핵심 지표)
    st.subheader("핵심 지표")
    cols = st.columns(5)
    cols[0].metric("매출액", format_krw(summary.get("revenue")))
    cols[1].metric("영업이익", format_krw(summary.get("operating_profit")))
    cols[2].metric("당기순이익", format_krw(summary.get("net_income")))
    cols[3].metric("총자산", format_krw(summary.get("total_assets")))
    cols[4].metric("자본총계", format_krw(summary.get("total_equity")))

    # 상세 (펼치기)
    with st.expander("📋 상세 재무제표", expanded=False):
        # 손익계산서
        st.markdown("**손익계산서**")
        income_data = {
            "항목": ["매출액", "매출원가", "매출총이익", "판관비", "영업이익", "영업외수익", "영업외비용", "법인세차감전손익", "법인세", "당기순이익"],
            "금액": [
                format_krw(full.get("revenue")),
                format_krw(full.get("cost_of_sales")),
                format_krw(full.get("gross_profit")),
                format_krw(full.get("selling_general_administrative_expenses")),
                format_krw(full.get("operating_profit")),
                format_krw(full.get("non_operating_income")),
                format_krw(full.get("non_operating_expenses")),
                format_krw(full.get("profit_before_tax_expense")),
                format_krw(full.get("income_tax_expense")),
                format_krw(full.get("net_income")),
            ]
        }
        st.dataframe(income_data, hide_index=True, use_container_width=True)

        # 재무상태표 - 자산
        st.markdown("**재무상태표 (자산)**")
        asset_data = {
            "항목": ["유동자산", "당좌자산", "재고자산", "비유동자산", "투자자산", "유형자산", "무형자산", "기타비유동자산", "자산총계"],
            "금액": [
                format_krw(full.get("current_assets")),
                format_krw(full.get("quick_assets")),
                format_krw(full.get("inventory_assets")),
                format_krw(full.get("non_current_assets")),
                format_krw(full.get("investment_assets")),
                format_krw(full.get("tangible_assets")),
                format_krw(full.get("intangible_assets")),
                format_krw(full.get("other_non_current_assets")),
                format_krw(full.get("total_assets")),
            ]
        }
        st.dataframe(asset_data, hide_index=True, use_container_width=True)

        # 재무상태표 - 부채/자본
        st.markdown("**재무상태표 (부채/자본)**")
        liability_data = {
            "항목": ["유동부채", "비유동부채", "부채총계", "자본금", "자본잉여금", "자본조정", "기타포괄손익누계", "이익잉여금", "결손금", "자본총계"],
            "금액": [
                format_krw(full.get("current_liabilities")),
                format_krw(full.get("non_current_liabilities")),
                format_krw(full.get("total_liabilities")),
                format_krw(full.get("capital")),
                format_krw(full.get("capital_surplus")),
                format_krw(full.get("capital_adjustment")),
                format_krw(full.get("accumulated_other_comprehensive_income")),
                format_krw(full.get("retained_earnings")),
                format_krw(full.get("deficit")),
                format_krw(full.get("total_equity")),
            ]
        }
        st.dataframe(liability_data, hide_index=True, use_container_width=True)

    if meta.get("updated_at"):
        st.caption(f"업데이트: {meta['updated_at'][:10]}")


def render_chat_response(data: dict):
    """Chat API 응답 렌더링"""
    answer = data.get("answer", "")
    sources = data.get("sources", {})

    # 마크다운 답변 표시
    st.markdown(answer)

    # 구조화 결과 (있으면 아래에 표시)
    sr = data.get("search_result", {})
    if sr:
        if sr.get("type") == "analytics" and sr.get("data"):
            render_analytics_results(sr)
        elif sr.get("type") == "financial":
            render_financial_results(sr)
        elif sr.get("results"):
            render_startup_results(sr)

    # 출처 정보 (하단에 작게)
    source_parts = []
    if sources.get("search"):
        source_parts.append(f"검색 {sources['search']}건")
    if sources.get("investments"):
        source_parts.append(f"투자 {sources['investments']}건")
    if sources.get("timeline"):
        source_parts.append(f"타임라인 {sources['timeline']}건")
    if sources.get("risks"):
        source_parts.append(f"리스크 {sources['risks']}건")

    if source_parts:
        st.caption(f"📊 {' · '.join(source_parts)}")


def render_error(data: dict):
    """에러 렌더링"""
    error = data.get("error", {})
    st.error(f"⚠️ {error.get('message', '알 수 없는 오류')}")


def render_response(data: dict, status: int):
    """응답 타입에 따라 렌더링"""
    if status != 200:
        render_error(data)
    elif data.get("type") == "chat":
        render_chat_response(data)
    elif data.get("type") == "analytics":
        render_analytics_results(data)
    elif data.get("type") == "financial":
        render_financial_results(data)
    elif data.get("type") == "web":
        render_web_results(data)
    elif data.get("results") is not None:
        if data.get("results"):
            render_startup_results(data)
        else:
            st.warning("검색 결과가 없습니다.")
            if data.get("suggestions"):
                st.markdown("**추천 검색어:** " + ", ".join(data["suggestions"]))
    else:
        render_error(data)


# 로그인 화면
if not st.session_state.logged_in:
    st.title("🔐 Lattice 로그인")

    with st.form("login_form"):
        alias_input = st.text_input("워크스페이스 ID", placeholder="워크스페이스 ID 입력")
        password_input = st.text_input("비밀번호", type="password", placeholder="비밀번호 (필요시)")
        submitted = st.form_submit_button("로그인", type="primary")

    if submitted:
        if alias_input:
            success, error_msg = login(alias_input, password_input)
            if success:
                st.rerun()
            else:
                st.error(error_msg)
        else:
            st.warning("워크스페이스 ID를 입력하세요.")

else:
    # 헤더
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🔍 Lattice")
    with col2:
        if st.session_state.is_admin:
            st.markdown("**🔑 Admin**")
        else:
            st.markdown(f"**{st.session_state.workspace_alias}**")
        if st.button("로그아웃"):
            logout()
            st.rerun()

    # 안내 메시지
    st.info("""
    **지원 기능:**
    - 🏢 **스타트업 검색**: "토스", "핀테크", "서울 시리즈A", "토스같은", "자본잠식 기업"
    - 📈 **재무제표**: "A기업 재무제표", "B사 2024년 실적"
    - 🌐 **웹검색**: "AI 최신 뉴스", "테슬라 주가"
    - 📊 **통계**: "핀테크 몇 개?", "산업별 분포"
    """)

    # Admin 디버그 모드
    if st.session_state.is_admin:
        st.session_state.debug_mode = st.checkbox("🐛 디버그 모드", value=st.session_state.debug_mode)

    # 채팅 히스토리 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg["content"])
            else:
                render_response(msg["data"], msg["status"])

                # 디버그 모드
                if st.session_state.debug_mode:
                    with st.expander("🐛 Debug", expanded=False):
                        # 출처 정보
                        matched = msg["data"].get("meta", {}).get("matched_conditions", {})
                        if matched:
                            st.markdown("**📍 컬럼 출처 (search_startups 뷰)**")
                            sources = get_condition_sources(matched)
                            for key, source in sources.items():
                                st.markdown(f"- `{key}`: {source}")
                            st.markdown("---")
                        st.json(msg["data"])

    # 채팅 입력
    if prompt := st.chat_input("검색어를 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # API 호출 및 응답
        with st.chat_message("assistant"):
            with st.spinner("검색 중..."):
                try:
                    result = call_chat_api(prompt)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "data": result["data"],
                        "status": result["status"],
                    })
                    render_response(result["data"], result["status"])

                    if st.session_state.debug_mode:
                        with st.expander("🐛 Debug", expanded=False):
                            # 출처 정보
                            matched = result["data"].get("meta", {}).get("matched_conditions", {})
                            if matched:
                                st.markdown("**📍 컬럼 출처 (search_startups 뷰)**")
                                sources = get_condition_sources(matched)
                                for key, source in sources.items():
                                    st.markdown(f"- `{key}`: {source}")
                                st.markdown("---")
                            st.json(result["data"])

                except requests.Timeout:
                    st.error("요청 시간 초과. 다시 시도해주세요.")
                except requests.RequestException as e:
                    st.error(f"네트워크 오류: {e}")
                except Exception as e:
                    st.error(f"오류 발생: {e}")
