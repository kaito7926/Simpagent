import { ShieldCheck, SquareDashedMousePointer, UserRoundCog } from "lucide-react";

const ITEMS = [
  {
    heading: "Mã truy cập ngắn hạn",
    body: "Mã truy cập chỉ được giữ trong bộ nhớ của giao diện.",
    icon: SquareDashedMousePointer,
  },
  {
    heading: "Cookie được bảo vệ",
    body: "Phiên làm mới không khả dụng cho JavaScript.",
    icon: ShieldCheck,
  },
  {
    heading: "Máy chủ là nguồn quyết định",
    body: "Vai trò, quyền và trạng thái tài khoản được kiểm tra lại phía máy chủ.",
    icon: UserRoundCog,
  },
] as const;

export function SecuritySummary() {
  return (
    <section className="security-summary" aria-labelledby="security-summary-heading">
      <h2 className="visually-hidden" id="security-summary-heading">
        Tóm tắt bảo vệ phiên
      </h2>
      {ITEMS.map((item) => {
        const Icon = item.icon;
        return (
          <article className="security-summary-item" key={item.heading}>
            <span className="security-node" aria-hidden="true" />
            <div className="security-summary-copy">
              <div className="security-summary-title-row">
                <Icon aria-hidden="true" size={18} strokeWidth={1.75} />
                <h3 className="label-heading">{item.heading}</h3>
              </div>
              <p className="body-copy max-copy">{item.body}</p>
            </div>
          </article>
        );
      })}
    </section>
  );
}
