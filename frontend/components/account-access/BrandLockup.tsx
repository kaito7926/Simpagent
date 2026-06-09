type BrandLockupProps = {
  authenticated: boolean;
};

export function BrandLockup({ authenticated }: BrandLockupProps) {
  return (
    <section className="brand-hero" aria-label="Giới thiệu SimpAgent">
      <p className="eyebrow">TRUY CẬP AN TOÀN</p>
      <div className="brand-hero-copy">
        <div className="brand-row">
          <span className="brand-mark-wrap" aria-hidden="true">
            <span className="brand-mark brand-mark-primary" />
            <span className="brand-mark brand-mark-secondary" />
          </span>
          <span className="brand-name">SimpAgent</span>
        </div>
        <h1 className="page-heading">
          {authenticated
            ? "Một điểm vào rõ ràng cho tài khoản và phiên."
            : "Một điểm vào rõ ràng cho tài khoản và phiên."}
        </h1>
        <p className="body-copy max-copy">
          Giai đoạn này chứng minh đăng ký, đăng nhập, phiên làm mới được bảo vệ và trạng thái danh tính hiện tại.
        </p>
      </div>
    </section>
  );
}
