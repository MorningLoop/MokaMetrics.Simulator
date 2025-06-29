import { useEffect, useRef } from "react";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    type ChartOptions,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface ProductionDataPoint {
    time: string;
    value: number;
}

interface ProductionChartProps {
    data: ProductionDataPoint[];
    title?: string;
    yAxisLabel?: string;
    color?: string;
    maxDataPoints?: number;
}

export function ProductionChart({
    data,
    title = "Production Rate",
    yAxisLabel = "Messages/Min",
    color = "rgb(59, 130, 246)",
    maxDataPoints = 20,
}: ProductionChartProps) {
    const chartRef = useRef<ChartJS<"line", number[], string>>(null);

    // Limit data points to prevent chart from becoming too cluttered
    const limitedData = data.slice(-maxDataPoints);

    const chartData = {
        labels: limitedData.map((point) => point.time),
        datasets: [
            {
                label: yAxisLabel,
                data: limitedData.map((point) => point.value),
                borderColor: color,
                backgroundColor: color.replace("rgb", "rgba").replace(")", ", 0.1)"),
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 5,
                pointBackgroundColor: color,
                pointBorderColor: "#ffffff",
                pointBorderWidth: 2,
            },
        ],
    };

    const options: ChartOptions<"line"> = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
            },
            tooltip: {
                mode: "index",
                intersect: false,
                backgroundColor: "rgba(0, 0, 0, 0.8)",
                titleColor: "#ffffff",
                bodyColor: "#ffffff",
                borderColor: color,
                borderWidth: 1,
            },
        },
        scales: {
            x: {
                display: true,
                title: {
                    display: true,
                    text: "Time",
                    color: "#6b7280",
                },
                grid: {
                    color: "rgba(0, 0, 0, 0.1)",
                },
                ticks: {
                    color: "#6b7280",
                    maxTicksLimit: 8,
                },
            },
            y: {
                display: true,
                title: {
                    display: true,
                    text: yAxisLabel,
                    color: "#6b7280",
                },
                grid: {
                    color: "rgba(0, 0, 0, 0.1)",
                },
                ticks: {
                    color: "#6b7280",
                },
                beginAtZero: true,
            },
        },
        interaction: {
            mode: "nearest",
            axis: "x",
            intersect: false,
        },
        animation: {
            duration: 750,
            easing: "easeInOutQuart",
        },
    };

    // Auto-update chart when data changes
    useEffect(() => {
        if (chartRef.current) {
            chartRef.current.update("none");
        }
    }, [data]);

    const currentValue = limitedData.length > 0 ? limitedData[limitedData.length - 1].value : 0;
    const previousValue = limitedData.length > 1 ? limitedData[limitedData.length - 2].value : 0;
    const trend = currentValue - previousValue;

    return (
        <Card>
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-medium flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        {title}
                    </CardTitle>
                    <div className="text-right">
                        <div className="text-2xl font-bold">{currentValue}</div>
                        <div
                            className={`text-sm flex items-center gap-1 ${
                                trend > 0 ? "text-green-600" : trend < 0 ? "text-red-600" : "text-gray-500"
                            }`}
                        >
                            {trend > 0 ? "↗" : trend < 0 ? "↘" : "→"}
                            {Math.abs(trend)} from last
                        </div>
                    </div>
                </div>
            </CardHeader>

            <CardContent>
                <div className="h-64 w-full">
                    <Line ref={chartRef} data={chartData} options={options} />
                </div>

                {limitedData.length === 0 && (
                    <div className="flex items-center justify-center h-64 text-muted-foreground">
                        <div className="text-center">
                            <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-50" />
                            <p>No data available</p>
                            <p className="text-sm">Chart will update when data is received</p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
