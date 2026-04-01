from __future__ import annotations

from html import escape

from cars_returns.models import AuditEvent, Order, ReturnRequest, User


def render_page(title: str, body: str, *, user: User | None = None, flash: str | None = None) -> str:
    nav = ""
    if user is not None:
        nav = (
            f"<nav><a href='/app'>Dashboard</a> "
            f"<a href='/manager/queue'>Manager Queue</a> "
            f"<form method='post' action='/logout' style='display:inline'>"
            f"<button type='submit'>Logout</button></form></nav>"
        )
    flash_html = f"<p class='flash'>{escape(flash)}</p>" if flash else ""
    return f"""
<!doctype html>
<html lang='en'>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>{escape(title)}</title>
    <style>
      :root {{
        --ink: #182126;
        --panel: #f6f1e8;
        --accent: #0f766e;
        --muted: #64748b;
        --warn: #9a3412;
      }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        background:
          radial-gradient(circle at top right, rgba(15,118,110,0.12), transparent 26rem),
          linear-gradient(180deg, #f3efe7 0%, #fcfaf6 100%);
        color: var(--ink);
      }}
      header, main {{ max-width: 960px; margin: 0 auto; padding: 24px; }}
      nav {{ display: flex; gap: 16px; align-items: center; margin-top: 12px; }}
      .hero {{ padding: 28px; background: rgba(255,255,255,0.82); border: 1px solid #d8d2c8; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }}
      .card {{ background: rgba(255,255,255,0.86); border: 1px solid #d8d2c8; padding: 18px; }}
      .flash {{ background: #fff4d6; border-left: 4px solid #d97706; padding: 12px; }}
      table {{ width: 100%; border-collapse: collapse; background: rgba(255,255,255,0.86); }}
      th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #ddd6cb; vertical-align: top; }}
      .badge {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 0.85rem; }}
      .badge-pending {{ background: #fef3c7; }}
      .badge-approved {{ background: #dcfce7; }}
      .badge-rejected {{ background: #fee2e2; }}
      .meta {{ color: var(--muted); font-size: 0.95rem; }}
      form.inline {{ display: inline; }}
      textarea, input[type='email'], input[type='password'], input[type='number'] {{
        width: 100%;
        padding: 10px;
        box-sizing: border-box;
        border: 1px solid #cbd5e1;
        background: #fff;
      }}
      button {{
        background: var(--accent);
        color: white;
        border: 0;
        padding: 10px 14px;
        cursor: pointer;
      }}
      .secondary {{ background: #475569; }}
      .danger {{ background: var(--warn); }}
      a {{ color: var(--accent); }}
    </style>
  </head>
  <body>
    <header>
      <div class='hero'>
        <h1>{escape(title)}</h1>
        {nav}
      </div>
    </header>
    <main>
      {flash_html}
      {body}
    </main>
  </body>
</html>
"""


def login_page(*, error: str | None = None) -> str:
    body = f"""
<section class='card'>
  <p>Sign in to manage orders, return requests, and approvals.</p>
  {"<p class='flash'>" + escape(error) + "</p>" if error else ""}
  <form method='post' action='/login'>
    <label>Email</label>
    <input type='email' name='email' required>
    <label>Password</label>
    <input type='password' name='password' required>
    <p class='meta'>Demo accounts: customer@example.com / customer123, agent@example.com / agent123, manager@example.com / manager123</p>
    <button type='submit'>Login</button>
  </form>
</section>
"""
    return render_page("Returns Console", body)


def dashboard_page(user: User, orders: list[Order], requests: list[ReturnRequest]) -> str:
    order_rows = "".join(
        f"<tr><td><a href='/orders/{escape(order.id)}'>{escape(order.id)}</a></td>"
        f"<td>{escape(order.customer_id)}</td>"
        f"<td>{len(order.items)} items</td>"
        f"<td>${order.shipping_paid:.2f}</td></tr>"
        for order in orders
    )
    request_rows = "".join(
        f"<tr><td><a href='/returns/{escape(request.id)}'>{escape(request.id)}</a></td>"
        f"<td>{escape(request.order_id)}</td>"
        f"<td>{status_badge(request.status)}</td></tr>"
        for request in requests
    )
    body = f"""
<div class='grid'>
  <section class='card'>
    <h2>Welcome, {escape(user.name)}</h2>
    <p class='meta'>Role: {escape(user.role)}</p>
    <p>This console tracks order returns, manager approvals, and the audit trail for each decision.</p>
  </section>
  <section class='card'>
    <h2>Open Work</h2>
    <p>{len([request for request in requests if request.status == "pending"])} pending return requests visible to you.</p>
  </section>
</div>
<section>
  <h2>Orders</h2>
  <table>
    <tr><th>Order</th><th>Customer</th><th>Items</th><th>Shipping Paid</th></tr>
    {order_rows}
  </table>
</section>
<section>
  <h2>Return Requests</h2>
  <table>
    <tr><th>Request</th><th>Order</th><th>Status</th></tr>
    {request_rows}
  </table>
</section>
"""
    return render_page("Returns Dashboard", body, user=user)


def order_detail_page(user: User, order: Order, *, return_eligible: bool) -> str:
    item_rows = "".join(
        f"<tr><td>{escape(item.sku)}</td><td>{escape(item.name)}</td><td>${item.unit_price:.2f}</td><td>{item.quantity}</td></tr>"
        for item in order.items
    )
    quantity_inputs = "".join(
        f"<label>{escape(item.name)} ({escape(item.sku)})</label>"
        f"<input type='number' min='0' max='{item.quantity}' name='qty_{escape(item.sku)}' value='0'>"
        for item in order.items
    )
    form = ""
    if return_eligible:
        form = f"""
<section class='card'>
  <h2>Create Return Request</h2>
  <form method='post' action='/orders/{escape(order.id)}/returns'>
    {quantity_inputs}
    <label>Notes</label>
    <textarea name='notes' rows='5'></textarea>
    <button type='submit'>Submit Return Request</button>
  </form>
</section>
"""
    else:
        form = "<p class='flash'>This order is outside the return window.</p>"
    body = f"""
<section class='card'>
  <h2>Order {escape(order.id)}</h2>
  <p class='meta'>Customer: {escape(order.customer_id)}</p>
  <table>
    <tr><th>SKU</th><th>Name</th><th>Unit Price</th><th>Quantity</th></tr>
    {item_rows}
  </table>
</section>
{form}
"""
    return render_page(f"Order {order.id}", body, user=user)


def return_detail_page(
    user: User,
    request: ReturnRequest,
    refund_total: float,
    audit_events: list[AuditEvent],
    *,
    can_review: bool,
) -> str:
    item_rows = "".join(
        f"<li>{escape(item.sku)} x {item.quantity}</li>"
        for item in request.requested_items
    )
    audit_rows = "".join(
        f"<li>{escape(event.action)} by {escape(event.actor_id)} at {escape(event.created_at.isoformat())}</li>"
        for event in audit_events
    )
    actions = ""
    if can_review and request.status == "pending":
        actions = f"""
<form class='inline' method='post' action='/returns/{escape(request.id)}/approve'>
  <button type='submit'>Approve</button>
</form>
<form class='inline' method='post' action='/returns/{escape(request.id)}/reject'>
  <button class='danger' type='submit'>Reject</button>
</form>
"""
    body = f"""
<section class='grid'>
  <div class='card'>
    <h2>Request {escape(request.id)}</h2>
    <p>Order: <a href='/orders/{escape(request.order_id)}'>{escape(request.order_id)}</a></p>
    <p>Status: {status_badge(request.status)}</p>
    <p>Refund total: ${refund_total:.2f}</p>
    <p>Notes</p>
    <p>{escape(request.notes)}</p>
    <ul>{item_rows}</ul>
    {actions}
  </div>
  <div class='card'>
    <h2>Audit Trail</h2>
    <ul>{audit_rows}</ul>
  </div>
</section>
"""
    return render_page(f"Return {request.id}", body, user=user)


def manager_queue_page(user: User, requests: list[ReturnRequest]) -> str:
    rows = "".join(
        f"<tr><td><a href='/returns/{escape(request.id)}'>{escape(request.id)}</a></td>"
        f"<td>{escape(request.order_id)}</td>"
        f"<td>{escape(request.customer_id)}</td>"
        f"<td>{status_badge(request.status)}</td></tr>"
        for request in requests
    )
    body = f"""
<section class='card'>
  <h2>Pending Review Queue</h2>
  <table>
    <tr><th>Request</th><th>Order</th><th>Customer</th><th>Status</th></tr>
    {rows}
  </table>
</section>
"""
    return render_page("Manager Queue", body, user=user)


def status_badge(status: str) -> str:
    css = {
        "pending": "badge-pending",
        "approved": "badge-approved",
        "rejected": "badge-rejected",
    }.get(status, "badge-pending")
    return f"<span class='badge {css}'>{escape(status.title())}</span>"
