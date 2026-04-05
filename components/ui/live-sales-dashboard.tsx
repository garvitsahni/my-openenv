import React, { FC } from 'react';
import { useRealtimeSalesData } from '@/demos/hooks/useRealtimeSalesData';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Zap, Target, DollarSign, Activity, Cpu, Hexagon } from 'lucide-react';

const CyberMetric: FC<{ title: string, value: any, unit?: string, icon: any, color: "cyan" | "pink" }> = ({ title, value, unit="", icon, color }) => (
  <Card className={`cyber-card relative overflow-hidden transition-all hover:scale-105 neon-border-${color}`}>
    <div className={`absolute top-0 right-0 p-4 opacity-10`}><Hexagon size={64}/></div>
    <CardHeader className="flex flex-row items-center justify-between pb-2">
      <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{title}</CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      <div className={`text-3xl font-extrabold tracking-tighter ${color === "cyan" ? "text-cyan-400" : "text-pink-500"}`}>
        {unit}{typeof value === 'number' ? value.toLocaleString(undefined, { minimumFractionDigits: 1 }) : value}
      </div>
    </CardContent>
  </Card>
);

export const SalesDashboard: FC = () => {
  const { totalRevenue, salesCount, averageSale, agentEfficiency, passRate, latestPayments, salesChartData } = useRealtimeSalesData();

  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-10 font-mono flex flex-col gap-8">
      <div className="flex justify-between items-end border-b border-white/10 pb-6">
        <div>
          <h1 className="text-5xl font-black italic tracking-tighter text-cyan-400 drop-shadow-[0_0_10px_#00f2ff]">HUD://SALES_GEN_OVAL</h1>
          <p className="text-muted-foreground mt-2 text-xs tracking-widest uppercase">System Status: Optimal | Frequency: 7860Hz</p>
        </div>
        <Badge className="bg-cyan-500 text-black font-bold animate-pulse">SYSTEM_ACTIVE</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <CyberMetric title="Operational Revenue" value={totalRevenue} unit="$" icon={<DollarSign className="text-green-400"/>} color="cyan"/>
        <CyberMetric title="Agent Efficiency" value={agentEfficiency} unit="%" icon={<Cpu className="text-cyan-400"/>} color="cyan"/>
        <CyberMetric title="Strategic Pass Rate" value={passRate} unit="%" icon={<Target className="text-pink-400"/>} color="pink"/>
        <CyberMetric title="AOV Threshold" value={averageSale} unit="$" icon={<Zap className="text-pink-400"/>} color="pink"/>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <Card className="lg:col-span-2 cyber-card">
          <CardHeader><CardTitle className="text-cyan-400 flex gap-2"><Activity size={20}/> REVENUE_STREAM_OS</CardTitle></CardHeader>
          <CardContent className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={salesChartData}>
                <defs>
                  <linearGradient id="cyan-glow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00f2ff" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#00f2ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.05} />
                <XAxis dataKey="time" hide />
                <YAxis hide />
                <Tooltip contentStyle={{ background: '#000', border: '1px solid #00f2ff', color: '#00f2ff' }} />
                <Area type="step" dataKey="sales" stroke="#00f2ff" strokeWidth={3} fillOpacity={1} fill="url(#cyan-glow)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="cyber-card">
          <CardHeader><CardTitle className="text-pink-500 font-bold uppercase tracking-widest text-sm">Real-time Order Feed</CardTitle></CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px] pr-4">
              {latestPayments.map(p => (
                <div key={p.id} className="flex justify-between p-4 border-b border-white/5 hover:bg-white/5 transition group">
                  <div>
                    <p className="font-black text-pink-400">${p.amount.toFixed(2)}</p>
                    <p className="text-[10px] text-muted-foreground uppercase">{p.product}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Badge variant="outline" className={`text-[10px] ${p.status === "PASS" ? "border-green-500 text-green-500" : "border-red-500 text-red-500"}`}>{p.status}</Badge>
                    <p className="text-[10px] font-mono text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">{p.id.substring(0,6)}</p>
                  </div>
                </div>
              ))}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
