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

# 세션 상태 초기화
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.workspace_alias = None
    st.session_state.workspace_id = None
    st.session_state.is_admin = False
    st.session_state.debug_mode = False
    st.session_state.messages = []


def login(alias: str) -> bool:
    """별칭으로 로그인 시도"""
    alias = alias.strip().lower()

    if alias == "admin":
        st.session_state.logged_in = True
        st.session_state.workspace_alias = "admin"
        st.session_state.workspace_id = None
        st.session_state.is_admin = True
        return True

    if alias in WORKSPACE_ALIASES:
        st.session_state.logged_in = True
        st.session_state.workspace_alias = alias
        st.session_state.workspace_id = WORKSPACE_ALIASES[alias]
        st.session_state.is_admin = False
        return True

    return False


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

    st.markdown(f"**검색 결과** ({meta.get('total', len(results))}건) · `{meta.get('route_type', '-')}`")

    if meta.get("matched_conditions"):
        st.caption(f"적용 조건: {meta['matched_conditions']}")
    if meta.get("reference_company"):
        st.caption(f"참조 기업: {meta['reference_company']}")

    for company in results:
        with st.expander(f"**{company['name']}** - {company.get('industry', '-')}"):
            cols = st.columns(4)
            cols[0].markdown(f"**대표:** {company.get('ceo_name', '-')}")
            cols[1].markdown(f"**지역:** {company.get('region', '-')}")
            cols[2].markdown(f"**라운드:** {company.get('round', '-')}")
            cols[3].markdown(f"**단계:** {company.get('stage', '-')}")

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
    """웹검색 결과 렌더링"""
    results = data.get("results", [])
    meta = data.get("meta", {})

    st.markdown(f"**🌐 웹 검색 결과** · `{meta.get('query', '')}`")

    if not results:
        st.info("검색 결과가 없습니다.")
        return

    for r in results:
        st.markdown(f"**[{r.get('title', '')}]({r.get('link', '')})**")
        st.caption(r.get("snippet", ""))
        st.markdown("---")


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
        submitted = st.form_submit_button("로그인", type="primary")

    if submitted:
        if alias_input:
            if login(alias_input):
                st.rerun()
            else:
                st.error("존재하지 않는 워크스페이스입니다.")
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
    - 🏢 **스타트업 검색**: "토스", "핀테크", "서울 시리즈A", "토스같은"
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
