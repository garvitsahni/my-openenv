import { useState, useEffect } from 'react';

export const useRealtimeSalesData = () => {
  const [metrics, setMetrics] = useState({
    totalRevenue: 0,
    salesCount: 0,
    averageSale: 0,
    agentEfficiency: 0,
    passRate: 0,
    latestPayments: [] as any[],
    salesChartData: [] as any[]
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('http://localhost:7860/dashboard/data');
        const data = await response.json();
        
        // Advanced Analytics
        const totalPasses = data.completed_episodes.filter((e: any) => e.status === "PASS").length;
        const passRate = data.stats.pass_rate;
        
        // Agent Efficiency Calculation: Pass Rate / Avg Step Count (Inverse)
        const avgSteps = data.completed_episodes.reduce((acc: any, curr: any) => acc + curr.steps, 0) / (data.completed_episodes.length || 1);
        const efficiency = (passRate / (avgSteps || 1)) * 10;
        
        setMetrics({
          totalRevenue: data.stats.avg_score * data.stats.total * 100,
          salesCount: data.stats.total,
          averageSale: data.stats.avg_score * 100,
          agentEfficiency: efficiency,
          passRate: passRate,
          latestPayments: data.completed_episodes.map((ep: any) => ({
            id: ep.episode_id,
            amount: ep.final_score * 100,
            product: `${ep.env} - ${ep.difficulty}`,
            status: ep.status,
            time: new Date(ep.time * 1000).toLocaleTimeString()
          })),
          salesChartData: data.completed_episodes.map((ep: any) => ({
            time: ep.difficulty,
            sales: ep.final_score * 100
          }))
        });

      } catch (error) {
        console.error("Dashboard Cyber-sync failed:", error);
      }
    };

    const interval = setInterval(fetchData, 2000);
    fetchData();
    return () => clearInterval(interval);
  }, []);

  return metrics;
};
