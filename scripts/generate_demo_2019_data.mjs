import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] || path.join(import.meta.dirname, ".."));
const baseDir = path.join(root, "demo_data", "2019");
const monthStart = new Date("2019-05-01T00:00:00");
const daysInMonth = 31;

const provinces = [
  { province: "广东省", city: "广州市", districts: ["天河区", "番禺区", "白云区"] },
  { province: "浙江省", city: "杭州市", districts: ["西湖区", "滨江区", "余杭区"] },
  { province: "江苏省", city: "南京市", districts: ["秦淮区", "玄武区"] },
  { province: "四川省", city: "成都市", districts: ["武侯区", "锦江区"] },
];

const orderSources = ["开放平台", "麦芽田订单", "合作优选商家下单", "客户端小程序下单", "商家端APP Android下单", "商家端APP iOS下单"];
const firstNames = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜";
const givenNames = ["明", "强", "芳", "娜", "勇", "杰", "敏", "磊", "军", "洋", "婷", "鹏", "霞", "辉", "宇", "浩", "鑫", "涛", "静", "超"];
const merchantWords = ["鲜食", "便利店", "餐饮", "优选", "生活馆", "果蔬", "烘焙", "咖啡", "茶饮", "超市", "小吃", "快餐"];

let seed = 201905;
function rand() {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 0x100000000;
}
function pick(items) {
  return items[Math.floor(rand() * items.length)];
}
function pad(value) {
  return String(value).padStart(2, "0");
}
function formatDate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
function formatDateTime(date) {
  return `${formatDate(date)} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}
function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60 * 1000);
}
function csvEscape(value) {
  const text = value == null ? "" : String(value);
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}
function writeCsv(filePath, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const content = rows.map((row) => row.map(csvEscape).join(",")).join("\r\n") + "\r\n";
  fs.writeFileSync(filePath, "\ufeff" + content, "utf8");
}

const partners = Array.from({ length: 12 }, (_, index) => {
  const region = provinces[index % provinces.length];
  const district = region.districts[index % region.districts.length];
  const id = String(201 + index);
  return {
    id,
    name: `${region.city}${district}同城配送服务中心`,
    province: region.province,
    city: region.city,
    district,
    regionText: `${region.province}/${region.city}/${district}`,
    openDate: `2019-${pad(1 + (index % 3))}-${pad(3 + index)}`,
  };
});

const riders = [];
for (const partner of partners) {
  for (let i = 0; i < 10; i += 1) {
    const riderNo = riders.length + 1;
    const hireDay = 1 + Math.floor(rand() * 120);
    const hireDate = addMinutes(new Date("2019-01-01T00:00:00"), hireDay * 24 * 60);
    riders.push({
      id: String(90000 + riderNo),
      name: `${pick(firstNames)}${pick(givenNames)}`,
      hireDate: formatDate(hireDate),
      status: rand() < 0.56 ? "全职" : "兼职",
      partner,
    });
  }
}

const merchants = [];
for (const partner of partners) {
  for (let i = 0; i < 16; i += 1) {
    const merchantNo = merchants.length + 1;
    const registerDay = 1 + Math.floor(rand() * 150);
    const registerDate = addMinutes(new Date("2019-01-01T00:00:00"), registerDay * 24 * 60);
    const baseName = `${partner.district}${pick(merchantWords)}${merchantNo}`;
    merchants.push({
      id: String(30000 + merchantNo),
      name: baseName,
      shopName: `${baseName}门店`,
      registerDate: formatDate(registerDate),
      status: "正常",
      partner,
    });
  }
}

const partnerRows = [["ID", "合伙人", "成立时间", "合伙人区域", "状态"]];
for (const partner of partners) {
  partnerRows.push([partner.id, partner.name, partner.openDate, partner.regionText, "正常"]);
}

const riderRows = [["帮手ID", "帮手姓名", "入职时间", "状态", "所属合伙人", "所属区域"]];
for (const rider of riders) {
  riderRows.push([rider.id, rider.name, rider.hireDate, rider.status, rider.partner.name, rider.partner.regionText]);
}

const merchantRows = [["商家ID", "商家名称", "商户名称", "所属合伙人", "所属区域", "注册时间", "状态"]];
for (const merchant of merchants) {
  merchantRows.push([merchant.id, merchant.name, merchant.shopName, merchant.partner.name, merchant.partner.regionText, merchant.registerDate, merchant.status]);
}

const orderRows = [[
  "订单编号", "合伙人ID", "合伙人", "商家ID", "商家名称", "商户名称", "用户ID", "配送员ID", "配送员", "在职状态",
  "订单状态", "客服编号", "下单来源", "添加时间", "支付时间", "接单时间", "取消时间", "完成时间",
  "订单价格", "应付金额", "实付金额", "总部优惠金额", "优惠金额", "优惠券ID", "营销优惠券ID",
  "帮手收入", "合伙人收入", "总部收入", "麦芽田收入", "保险费",
]];

let orderSeq = 1;
for (let day = 0; day < daysInMonth; day += 1) {
  const current = new Date(monthStart.getTime() + day * 24 * 60 * 60 * 1000);
  const weekday = current.getDay();
  const dailyBase = 840 + Math.floor(rand() * 260) + (weekday === 0 || weekday === 6 ? 120 : 0);
  const dailyOrders = day >= 14 && day <= 18 ? dailyBase + 260 : dailyBase;

  for (let i = 0; i < dailyOrders; i += 1) {
    const partner = pick(partners);
    const partnerMerchants = merchants.filter((item) => item.partner.id === partner.id);
    const partnerRiders = riders.filter((item) => item.partner.id === partner.id);
    const merchant = pick(partnerMerchants);
    const rider = pick(partnerRiders);
    const hourRoll = rand();
    const hour = hourRoll < 0.08 ? Math.floor(rand() * 7) : hourRoll < 0.75 ? 9 + Math.floor(rand() * 11) : 20 + Math.floor(rand() * 4);
    const minute = Math.floor(rand() * 60);
    const second = Math.floor(rand() * 60);
    const createTime = new Date(current.getFullYear(), current.getMonth(), current.getDate(), hour, minute, second);
    const isPaid = rand() > 0.08;
    const payTime = isPaid ? addMinutes(createTime, 1 + Math.floor(rand() * 8)) : null;
    const completionTarget = partner.id === "203" || partner.id === "208" ? 0.72 : partner.id === "205" ? 0.80 : 0.90;
    const isCompleted = rand() < completionTarget;
    const willAccept = isCompleted || rand() < 0.42;
    const acceptDelay = hour >= 23 && rand() < 0.12 ? 20 + Math.floor(rand() * 80) : 2 + Math.floor(rand() * 18);
    const acceptTime = willAccept ? addMinutes(createTime, acceptDelay) : null;
    const completeTime = isCompleted && acceptTime ? addMinutes(acceptTime, 12 + Math.floor(rand() * 42)) : null;
    const cancelTime = !isCompleted ? addMinutes(payTime || createTime, 2 + Math.floor(rand() * 35)) : null;
    const orderPrice = 18 + rand() * 55;
    const hqDiscount = rand() < 0.35 ? 1 + rand() * 5 : 0;
    const partnerDiscount = rand() < 0.42 ? 1 + rand() * 6 : 0;
    const amountPayable = Math.max(orderPrice - hqDiscount - partnerDiscount, 1);
    const amountPaid = isPaid ? amountPayable : 0;
    const riderIncome = isCompleted ? 4.2 + rand() * 4.5 : 0;
    const partnerIncome = isCompleted ? 1.1 + rand() * 2.6 : 0;
    const hqIncome = isCompleted ? 0.7 + rand() * 1.3 : 0;
    const maiyatianIncome = isCompleted ? 0.2 + rand() * 0.5 : 0;
    const insuranceFee = isCompleted ? 0.08 + rand() * 0.18 : 0;
    const hasMarketing = rand() < 0.16;
    const status = isCompleted ? "已完成" : "已取消";
    const orderId = `201905${String(orderSeq).padStart(8, "0")}`;

    orderRows.push([
      orderId,
      partner.id,
      partner.name,
      merchant.id,
      merchant.name,
      merchant.shopName,
      String(700000 + Math.floor(rand() * 12000)),
      rider.id,
      rider.name,
      rider.status,
      status,
      `CS${100 + Math.floor(rand() * 20)}`,
      pick(orderSources),
      formatDateTime(createTime),
      payTime ? formatDateTime(payTime) : "",
      acceptTime ? formatDateTime(acceptTime) : "",
      cancelTime ? formatDateTime(cancelTime) : "",
      completeTime ? formatDateTime(completeTime) : "",
      orderPrice.toFixed(2),
      amountPayable.toFixed(2),
      amountPaid.toFixed(2),
      hqDiscount.toFixed(2),
      partnerDiscount.toFixed(2),
      partnerDiscount > 0 ? `C${orderSeq}` : "",
      hasMarketing ? `M${orderSeq}` : "",
      riderIncome.toFixed(2),
      partnerIncome.toFixed(2),
      hqIncome.toFixed(2),
      maiyatianIncome.toFixed(2),
      insuranceFee.toFixed(2),
    ]);
    orderSeq += 1;
  }
}

writeCsv(path.join(baseDir, "partners", "2019演示合伙人信息.csv"), partnerRows);
writeCsv(path.join(baseDir, "riders", "2019演示帮手信息.csv"), riderRows);
writeCsv(path.join(baseDir, "merchants", "2019演示商户信息.csv"), merchantRows);
writeCsv(path.join(baseDir, "orders_raw", "2019年5月演示订单明细.csv"), orderRows);

console.log(`Generated 2019 demo data in ${baseDir}`);
console.log(`Partners: ${partners.length}`);
console.log(`Riders: ${riders.length}`);
console.log(`Merchants: ${merchants.length}`);
console.log(`Orders: ${orderRows.length - 1}`);
