// 排列5开奖数据代理 - Vercel Serverless
// 用 Vercel 的 IP 抓取（不会被墙）

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  try {
    // 彩经网
    const resp = await fetch('https://m.cjcp.com.cn/kaijiang/pl5/', {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
    });
    const html = await resp.text();
    
    // 找最新期号和号码
    const periodMatch = html.match(/第(\d{7})期开奖/);
    if (!periodMatch) {
      return res.json({ success: false, error: '未找到期号' });
    }
    
    const period = parseInt(periodMatch[1]);
    const idx = periodMatch.index;
    const chunk = html.substring(idx, idx + 800);
    const nums = chunk.match(/qiu_red">(\d)<\/span>/g);
    
    if (!nums || nums.length < 5) {
      return res.json({ success: false, error: '未找到号码' });
    }
    
    const digits = nums.map(n => n.match(/>(\d)</)[1]).join('');
    return res.json({ 
      success: true, 
      period, 
      winning: digits.substring(0, 4), 
      full: digits.substring(0, 5),
      source: '彩经网(Vercel代理)' 
    });
    
  } catch (e) {
    return res.json({ success: false, error: e.message });
  }
}
