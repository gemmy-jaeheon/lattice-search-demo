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


def call_search_api(query: str) -> dict:
    """검색 API 호출"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    if not st.session_state.is_admin and st.session_state.workspace_id:
        headers["x-workspace-id"] = st.session_state.workspace_id

    response = requests.post(
        API_URL,
        headers=headers,
        json={"query": query},
        timeout=30,
    )
    return {"data": response.json(), "status": response.status_code}


def render_startup_results(data: dict):
    """스타트업 검색 결과 렌더링"""
    meta = data.get("meta", {})
    results = data.get("results", [])
    matched_conditions = meta.get("matched_conditions", {})

    st.markdown(f"**검색 결과** ({meta.get('total', len(results))}건) · `{meta.get('route_type', '-')}`")

    if matched_conditions:
        st.caption(f"적용 조건: {matched_conditions}")
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


def render_error(data: dict):
    """에러 렌더링"""
    error = data.get("error", {})
    st.error(f"⚠️ {error.get('message', '알 수 없는 오류')}")


def render_response(data: dict, status: int):
    """응답 타입에 따라 렌더링"""
    if status != 200:
        render_error(data)
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
                    result = call_search_api(prompt)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "data": result["data"],
                        "status": result["status"],
                    })
                    render_response(result["data"], result["status"])

                    if st.session_state.debug_mode:
                        with st.expander("🐛 Debug", expanded=False):
                            st.json(result["data"])

                except requests.Timeout:
                    st.error("요청 시간 초과. 다시 시도해주세요.")
                except requests.RequestException as e:
                    st.error(f"네트워크 오류: {e}")
                except Exception as e:
                    st.error(f"오류 발생: {e}")
