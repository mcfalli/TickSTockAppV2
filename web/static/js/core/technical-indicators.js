// ==========================================================================
// TICKSTOCK TECHNICAL INDICATORS - SPRINT 12 PHASE 2
// ==========================================================================
// VERSION: 1.0.0 - Sprint 12 Phase 2 Technical Analysis
// PURPOSE: Technical indicator calculations for chart overlays
// ==========================================================================

class TechnicalIndicators {
    constructor() {
        this.indicators = new Map();
    }

    // Simple Moving Average (SMA)
    calculateSMA(data, period = 20) {
        if (!data || data.length < period) return [];
        
        const sma = [];
        for (let i = period - 1; i < data.length; i++) {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j].close;
            }
            sma.push({
                x: data[i].timestamp,
                y: sum / period
            });
        }
        return sma;
    }

    // Exponential Moving Average (EMA)
    calculateEMA(data, period = 20) {
        if (!data || data.length < period) return [];
        
        const multiplier = 2 / (period + 1);
        const ema = [];
        
        // Start with SMA for the first value
        let sum = 0;
        for (let i = 0; i < period; i++) {
            sum += data[i].close;
        }
        let emaValue = sum / period;
        ema.push({
            x: data[period - 1].timestamp,
            y: emaValue
        });

        // Calculate EMA for remaining values
        for (let i = period; i < data.length; i++) {
            emaValue = (data[i].close - emaValue) * multiplier + emaValue;
            ema.push({
                x: data[i].timestamp,
                y: emaValue
            });
        }
        return ema;
    }

    // Relative Strength Index (RSI)
    calculateRSI(data, period = 14) {
        if (!data || data.length < period + 1) return [];
        
        const rsi = [];
        const gains = [];
        const losses = [];

        // Calculate initial gains and losses
        for (let i = 1; i <= period; i++) {
            const change = data[i].close - data[i - 1].close;
            gains.push(change > 0 ? change : 0);
            losses.push(change < 0 ? Math.abs(change) : 0);
        }

        // Calculate initial average gain and loss
        let avgGain = gains.reduce((sum, gain) => sum + gain, 0) / period;
        let avgLoss = losses.reduce((sum, loss) => sum + loss, 0) / period;

        // Calculate RSI for each subsequent period
        for (let i = period; i < data.length; i++) {
            const change = data[i].close - data[i - 1].close;
            const gain = change > 0 ? change : 0;
            const loss = change < 0 ? Math.abs(change) : 0;

            // Smoothed averages
            avgGain = (avgGain * (period - 1) + gain) / period;
            avgLoss = (avgLoss * (period - 1) + loss) / period;

            const rs = avgGain / avgLoss;
            const rsiValue = 100 - (100 / (1 + rs));

            rsi.push({
                x: data[i].timestamp,
                y: rsiValue
            });
        }
        return rsi;
    }

    // Moving Average Convergence Divergence (MACD)
    calculateMACD(data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
        if (!data || data.length < slowPeriod) return { macd: [], signal: [], histogram: [] };

        const fastEMA = this.calculateEMA(data, fastPeriod);
        const slowEMA = this.calculateEMA(data, slowPeriod);
        
        if (fastEMA.length === 0 || slowEMA.length === 0) {
            return { macd: [], signal: [], histogram: [] };
        }

        // Calculate MACD line
        const macdLine = [];
        const startIndex = Math.max(0, slowEMA.length - fastEMA.length);
        
        for (let i = startIndex; i < Math.min(fastEMA.length, slowEMA.length); i++) {
            macdLine.push({
                x: fastEMA[i].x,
                close: fastEMA[i].y - slowEMA[i].y
            });
        }

        // Calculate Signal line (EMA of MACD)
        const signalLine = this.calculateEMA(macdLine, signalPeriod);
        
        // Calculate Histogram
        const histogram = [];
        for (let i = 0; i < Math.min(macdLine.length, signalLine.length); i++) {
            if (macdLine[i + (macdLine.length - signalLine.length)]) {
                histogram.push({
                    x: signalLine[i].x,
                    y: macdLine[i + (macdLine.length - signalLine.length)].close - signalLine[i].y
                });
            }
        }

        return {
            macd: macdLine.map(point => ({ x: point.x, y: point.close })),
            signal: signalLine,
            histogram: histogram
        };
    }

    // Bollinger Bands
    calculateBollingerBands(data, period = 20, stdDev = 2) {
        if (!data || data.length < period) return { upper: [], middle: [], lower: [] };

        const sma = this.calculateSMA(data, period);
        const upper = [];
        const lower = [];

        for (let i = period - 1; i < data.length; i++) {
            // Calculate standard deviation for this period
            const slice = data.slice(i - period + 1, i + 1);
            const mean = slice.reduce((sum, item) => sum + item.close, 0) / period;
            const variance = slice.reduce((sum, item) => sum + Math.pow(item.close - mean, 2), 0) / period;
            const standardDeviation = Math.sqrt(variance);

            const smaIndex = i - period + 1;
            if (smaIndex >= 0 && smaIndex < sma.length) {
                upper.push({
                    x: data[i].timestamp,
                    y: sma[smaIndex].y + (stdDev * standardDeviation)
                });
                lower.push({
                    x: data[i].timestamp,
                    y: sma[smaIndex].y - (stdDev * standardDeviation)
                });
            }
        }

        return {
            upper: upper,
            middle: sma,
            lower: lower
        };
    }

    // Volume indicators
    calculateVolumeMA(data, period = 20) {
        if (!data || data.length < period) return [];
        
        const volumeMA = [];
        for (let i = period - 1; i < data.length; i++) {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += data[i - j].volume || 0;
            }
            volumeMA.push({
                x: data[i].timestamp,
                y: sum / period
            });
        }
        return volumeMA;
    }

    // Apply indicator to chart data
    applyIndicator(indicatorType, data, options = {}) {
        try {
            switch (indicatorType.toLowerCase()) {
                case 'sma':
                    return this.calculateSMA(data, options.period || 20);
                case 'ema':
                    return this.calculateEMA(data, options.period || 20);
                case 'rsi':
                    return this.calculateRSI(data, options.period || 14);
                case 'macd':
                    return this.calculateMACD(
                        data, 
                        options.fastPeriod || 12,
                        options.slowPeriod || 26,
                        options.signalPeriod || 9
                    );
                case 'bollinger':
                case 'bb':
                    return this.calculateBollingerBands(
                        data, 
                        options.period || 20,
                        options.stdDev || 2
                    );
                case 'volume_ma':
                    return this.calculateVolumeMA(data, options.period || 20);
                default:
                    console.warn(`[TechnicalIndicators] Unknown indicator: ${indicatorType}`);
                    return [];
            }
        } catch (error) {
            console.error(`[TechnicalIndicators] Error calculating ${indicatorType}:`, error);
            return [];
        }
    }

    // Get available indicators
    getAvailableIndicators() {
        return [
            { id: 'sma', name: 'Simple Moving Average', category: 'trend' },
            { id: 'ema', name: 'Exponential Moving Average', category: 'trend' },
            { id: 'rsi', name: 'Relative Strength Index', category: 'momentum' },
            { id: 'macd', name: 'MACD', category: 'momentum' },
            { id: 'bollinger', name: 'Bollinger Bands', category: 'volatility' },
            { id: 'volume_ma', name: 'Volume Moving Average', category: 'volume' }
        ];
    }

    // Validate indicator parameters
    validateParameters(indicatorType, options) {
        const validations = {
            sma: () => options.period > 0 && options.period <= 200,
            ema: () => options.period > 0 && options.period <= 200,
            rsi: () => options.period > 0 && options.period <= 50,
            macd: () => options.fastPeriod < options.slowPeriod && options.signalPeriod > 0,
            bollinger: () => options.period > 0 && options.stdDev > 0,
            volume_ma: () => options.period > 0 && options.period <= 200
        };

        const validator = validations[indicatorType.toLowerCase()];
        return validator ? validator() : false;
    }
}

// Global technical indicators instance
const technicalIndicators = new TechnicalIndicators();

// Export for use in other modules
window.TechnicalIndicators = TechnicalIndicators;
window.technicalIndicators = technicalIndicators;