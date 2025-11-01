// django_ma/static/js/common/part_branch_selector.js
window.loadPartsAndBranches = async function (rootId = "manage-structure") {
  const root =
    document.getElementById(rootId) ||
    document.getElementById("manage-rate"); // 요율변경도 지원

  if (!root) return;

  const partSelect = document.getElementById("partSelect");
  const branchSelect = document.getElementById("branchSelect");
  if (!partSelect || !branchSelect) return;

  try {
    // ✅ 부서 목록 가져오기
    const res = await fetch("/partner/ajax/fetch-parts/");
    const data = await res.json();

    partSelect.innerHTML = "";
    if (data.parts?.length) {
      for (const part of data.parts) {
        const opt = document.createElement("option");
        opt.value = part;
        opt.textContent = part;
        partSelect.appendChild(opt);
      }
      console.log("✅ 부서 목록 로드 완료");
    } else {
      partSelect.innerHTML = `<option value="">부서 없음</option>`;
    }

    // ✅ 부서 선택 → 지점 목록 로드
    partSelect.addEventListener("change", async () => {
      const part = partSelect.value;
      branchSelect.innerHTML = `<option>불러오는 중...</option>`;
      if (!part) return;

      const res2 = await fetch(`/partner/ajax/fetch-branches/?part=${encodeURIComponent(part)}`);
      const data2 = await res2.json();

      branchSelect.innerHTML = "";
      if (data2.branches?.length) {
        for (const br of data2.branches) {
          const opt = document.createElement("option");
          opt.value = br;
          opt.textContent = br;
          branchSelect.appendChild(opt);
        }
        branchSelect.disabled = false;
        console.log("✅ 지점 목록 로드 완료");
      } else {
        branchSelect.innerHTML = `<option value="">지점 없음</option>`;
      }
    });
  } catch (err) {
    console.error("❌ 부서/지점 목록 로드 오류:", err);
    partSelect.innerHTML = `<option value="">로드 실패</option>`;
  }
};
