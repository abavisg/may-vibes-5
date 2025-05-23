import 'package:flutter/material.dart';

class Signal {
  final String id;
  final String symbol;
  final String timestamp;
  final String typeOfData;
  final String type;  // This corresponds to signal_type (BUY/SELL)
  final double? entryPrice;
  final double? stopLoss;
  final double? takeProfit;
  final Map<String, dynamic> pattern;

  Signal({
    required this.id,
    required this.symbol,
    required this.timestamp,
    required this.typeOfData,
    required this.type,
    this.entryPrice,
    this.stopLoss,
    this.takeProfit,
    required this.pattern,
  });

  factory Signal.fromJson(Map<String, dynamic> json) {
    return Signal(
      id: json['id'] ?? '',
      symbol: json['symbol'] ?? '',
      timestamp: json['timestamp'] ?? '',
      typeOfData: json['type_of_data'] ?? 'UNKNOWN',
      type: json['type'] ?? '',
      entryPrice: json['entry_price']?.toDouble(),
      stopLoss: json['stop_loss']?.toDouble(),
      takeProfit: json['take_profit']?.toDouble(),
      pattern: json['pattern'] ?? {},
    );
  }

  DateTime get timestampDateTime {
    try {
      // Try to parse as integer (Unix timestamp)
      if (timestamp.contains(RegExp(r'^[0-9]+$'))) {
        return DateTime.fromMillisecondsSinceEpoch(
          // Convert from seconds to milliseconds if needed
          timestamp.length <= 10 
              ? int.parse(timestamp) * 1000 
              : int.parse(timestamp)
        );
      }
      // Try to parse as standard ISO format
      return DateTime.parse(timestamp);
    } catch (e) {
      return DateTime.now();
    }
  }

  String get formattedTimestamp {
    try {
      final dt = timestampDateTime;
      return '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
    } catch (e) {
      return timestamp;
    }
  }

  Color get signalColor {
    switch (type.toUpperCase()) {
      case 'BUY':
        return Colors.green;
      case 'SELL':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData get signalIcon {
    switch (type.toUpperCase()) {
      case 'BUY':
        return Icons.arrow_upward;
      case 'SELL':
        return Icons.arrow_downward;
      default:
        return Icons.remove;
    }
  }

  String get patternType => pattern['type'] ?? 'Unknown';
  
  int get patternStrength {
    final strength = pattern['confidence'] ?? pattern['strength'] ?? 0.0;
    return (strength is num) ? strength.round() : 0;
  }
} 