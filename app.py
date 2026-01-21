import streamlit as st
import requests

st.set_page_config(page_title="Lattice 검색", page_icon="🔍", layout="wide")

API_URL = st.secrets["SUPABASE_API_URL"]
API_KEY = st.secrets["SUPABASE_ANON_KEY"]
WORKSPACE_ID = st.secrets.get("WORKSPACE_ID", "")

st.title("🔍 Lattice 스타트업 검색")

st.markdown("""
검색 예시:
- **키워드**: `토스`, `카카오` (회사명 직접 검색)
- **조건**: `핀테크`, `서울 스타트업`, `시리즈A` (산업/지역/라운드)
- **유사**: `토스랑 비슷한`, `A기업과 유사한` (임베딩 검색)
- **복합**: `서울에서 토스랑 비슷한` (조건 + 유사)
- **통계**: `산업별 분포`, `평균 밸류에이션` (집계)
""")

query = st.text_input("검색어", placeholder="예: 서울에 있는 핀테크")

if st.button("검색", type="primary") and query.strip():
    with st.spinner("검색 중..."):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        if WORKSPACE_ID:
            headers["x-workspace-id"] = WORKSPACE_ID

        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json={"query": query},
                timeout=30,
            )
            data = response.json()

            if response.status_code != 200:
                st.error(f"오류: {data.get('error', {}).get('message', '알 수 없는 오류')}")
            elif data.get("type") == "analytics":
                st.subheader("📊 통계 결과")
                meta = data.get("meta", {})
                st.caption(meta.get("description", ""))

                if data.get("data"):
                    st.dataframe(data["data"], use_container_width=True)
                else:
                    st.info("집계 결과가 없습니다.")

                if data.get("clarification_options"):
                    st.markdown("**선택지:** " + ", ".join(data["clarification_options"]))
            elif data.get("results"):
                meta = data.get("meta", {})
                st.subheader(f"🏢 검색 결과 ({meta.get('total', len(data['results']))}건)")
                st.caption(f"검색 타입: `{meta.get('route_type', '-')}`")

                if meta.get("matched_conditions"):
                    st.caption(f"적용 조건: {meta['matched_conditions']}")
                if meta.get("reference_company"):
                    st.caption(f"참조 기업: {meta['reference_company']}")

                for company in data["results"]:
                    with st.expander(f"**{company['name']}** - {company.get('industry', '-')}"):
                        cols = st.columns(3)
                        cols[0].markdown(f"**지역:** {company.get('region', '-')} / {company.get('city', '-')}")
                        cols[1].markdown(f"**라운드:** {company.get('round', '-')}")
                        cols[2].markdown(f"**단계:** {company.get('stage', '-')}")

                        if company.get("summary"):
                            st.markdown(company["summary"])

                        if company.get("technologies"):
                            st.markdown(f"**기술:** {company['technologies']}")

                        if company.get("pre_money_valuation"):
                            val = company["pre_money_valuation"]
                            st.markdown(f"**Pre-money:** {val / 100_000_000:.0f}억원")
            else:
                st.warning("검색 결과가 없습니다.")
                if data.get("suggestions"):
                    st.markdown("**추천 검색어:** " + ", ".join(data["suggestions"]))

        except requests.Timeout:
            st.error("요청 시간 초과. 다시 시도해주세요.")
        except requests.RequestException as e:
            st.error(f"네트워크 오류: {e}")
        except Exception as e:
            st.error(f"오류 발생: {e}")
