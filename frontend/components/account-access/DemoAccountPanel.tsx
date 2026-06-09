import { ActionButton } from "./ActionButton";

type DemoAccountPanelProps = {
  onFillUser: () => void;
  onFillAdmin: () => void;
};

export function DemoAccountPanel({ onFillUser, onFillAdmin }: DemoAccountPanelProps) {
  return (
    <section className="demo-panel" aria-labelledby="demo-panel-heading">
      <h3 className="label-heading" id="demo-panel-heading">
        Tài khoản demo cục bộ
      </h3>
      <p className="body-copy max-copy">
        Chỉ dùng cho bản demo phát triển trên máy này. Không sử dụng các thông tin này ở môi trường thật.
      </p>
      <div className="demo-actions">
        <ActionButton type="button" variant="secondary" onClick={onFillUser}>
          Điền tài khoản Người dùng
        </ActionButton>
        <ActionButton type="button" variant="secondary" onClick={onFillAdmin}>
          Điền tài khoản Quản trị viên
        </ActionButton>
      </div>
    </section>
  );
}
