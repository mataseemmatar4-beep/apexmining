import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apex.db")

PLANS = [
  # slug, name, price, rate, days, hash, algo, badge, tagline, features
  ("starter","Starter",50,0.005,30,"50 GH/s","SHA-256",None,"Perfect entry-level contract for first-time miners.","Daily auto payout|Instant activation|24/7 monitoring|Email support"),
  ("advanced","Advanced",200,0.006,45,"250 GH/s","SHA-256","POPULAR","Our most popular plan — best balance of price and returns.","Daily auto payout|Priority activation|24/7 monitoring|Live chat support|Profit compounding"),
  ("pro","Pro",500,0.007,60,"750 GH/s","SHA-256",None,"Built for serious miners who want higher daily yields.","Daily auto payout|Priority activation|Dedicated account manager|Live chat support|Profit compounding|Early withdrawal"),
  ("elite","Elite",1500,0.008,90,"2.5 TH/s","SHA-256","BEST VALUE","Maximum returns for committed investors.","Daily auto payout|Instant activation|Dedicated manager|Priority withdrawals|Profit compounding|VIP support"),
  ("institutional","Institutional",5000,0.009,120,"10 TH/s","SHA-256","VIP","Enterprise-grade hashpower for funds and high-net-worth clients.","All Elite benefits|Custom contract terms|Legal & compliance support|Direct wire deposits|Personal onboarding"),
  ("eth-starter","ETH Starter",100,0.0055,30,"120 MH/s","Ethash",None,"Ethereum mining entry contract.","Daily payout|ETH rewards|Low entry"),
  ("eth-pro","ETH Pro",800,0.0075,60,"1.2 GH/s","Ethash","HOT","High-yield Ethereum contract with compounding.","Daily payout|Compounding|Priority support"),
  ("ltc-starter","LTC Starter",75,0.005,30,"300 MH/s","Scrypt",None,"Litecoin mining for quick daily payouts.","Daily payout|LTC rewards|Instant start"),
  ("btc-max","BTC Max",2500,0.0085,90,"4 TH/s","SHA-256",None,"High-power Bitcoin contract for maximum daily yield.","Daily payout|Dedicated node|Priority withdrawals"),
  ("cloud-flex","Cloud Flex",1000,0.0065,45,"1 TH/s","SHA-256",None,"Flexible contract — switch algorithms anytime.","Flexible algo|Daily payout|Compounding"),
]

POSTS = [
  ("bitcoin-halving-2026","Bitcoin Halving 2026: What It Means for Cloud Miners",
   "The 2026 halving is upon us. Here's how it reshapes profitability for cloud mining contracts.",
   "The Bitcoin halving reduces block rewards by 50%, historically triggering price rallies and a shift toward efficient mining operations. For cloud miners, this means: (1) mining difficulty adjustments, (2) increased demand for hashpower, (3) new arbitrage opportunities across contracts. At ApexMining, our institutional partnerships keep our rates stable through the halving cycle.",
   "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=1200&q=80","Markets"),
  ("green-mining-2026","The Rise of Green Cloud Mining",
   "Renewable-powered data centers now dominate 60% of global hashpower. Here's why it matters.",
   "Sustainability is no longer optional. Our Icelandic and Norwegian facilities run entirely on geothermal and hydroelectric power, cutting operational costs and passing savings to clients. Green mining isn't just good ethics — it's better economics.",
   "https://images.unsplash.com/photo-1466611653911-95081537e5b7?w=1200&q=80","Industry"),
  ("how-to-choose-plan","How to Choose the Right Mining Plan in 2026",
   "Not all contracts are equal. A practical guide to matching hashpower with your goals.",
   "Consider three factors: budget, time horizon, and risk tolerance. Starter plans suit first-timers testing the waters. Advanced and Pro plans maximize returns for medium-term investors. Elite and Institutional are for high-net-worth individuals seeking maximum exposure.",
   "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200&q=80","Guides"),
  ("security-best-practices","Security Best Practices for Cloud Mining Accounts",
   "From 2FA to cold storage — how to protect your mining earnings.",
   "Enable two-factor authentication. Use unique passwords. Whitelist withdrawal addresses. Never share your referral code publicly without understanding the risks. Our platform supports all of these measures out of the box.",
   "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=1200&q=80","Security"),
  ("tax-guide-2026","Crypto Mining Tax Guide 2026",
   "How mining profits are taxed in the US, EU and Asia — and how to stay compliant.",
   "Mining income is generally treated as ordinary income at the time of receipt. Capital gains apply upon disposal. Our platform provides detailed exportable reports to simplify your filing.",
   "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1200&q=80","Guides"),
  ("apex-expansion","ApexMining Opens New Data Center in Singapore",
   "Expanding our Asian footprint with a 40 MW facility.",
   "Our fifth data center went live this month, adding 40 MW of dedicated capacity and reducing latency for clients across Southeast Asia. The facility operates on a mix of solar and grid power.",
   "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&q=80","News"),
]

def init():
    con = sqlite3.connect(DB)
    con.executescript(open(os.path.join(os.path.dirname(__file__),"schema.sql")).read())
    if not con.execute("SELECT 1 FROM plans LIMIT 1").fetchone():
        con.executemany("""INSERT INTO plans (slug,name,price,daily_rate,duration,hashpower,algo,badge,tagline,features)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""", PLANS)
    if not con.execute("SELECT 1 FROM posts LIMIT 1").fetchone():
        con.executemany("""INSERT INTO posts (slug,title,excerpt,body,image,tag)
                           VALUES (?,?,?,?,?,?)""", POSTS)
    con.commit(); con.close()

if __name__ == "__main__":
    init(); print("[+] database initialized")
