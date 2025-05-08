import 'package:flutter/material.dart';
import 'models/signal.dart';
import 'services/signal_service.dart';
import 'package:logger/logger.dart';

final logger = Logger();

void main() {
  runApp(const SignalRelayApp());
}

// App theme colors
class AppTheme {
  static const Color background = Color(0xFF121212);
  static const Color cardBackground = Color(0xFF1E1E1E);
  static const Color primary = Color(0xFF3498DB);
  static const Color textPrimary = Color(0xFFE0E0E0);
  static const Color textSecondary = Color(0xFFAAAAAA);
  static const Color buyColor = Color(0xFF4CAF50);
  static const Color sellColor = Color(0xFFE57373);
  static const Color divider = Color(0xFF333333);
}

class SignalRelayApp extends StatefulWidget {
  const SignalRelayApp({super.key});
  @override
  State<SignalRelayApp> createState() => _SignalRelayAppState();
}

class _SignalRelayAppState extends State<SignalRelayApp> {
  List<Signal> signals = [];
  bool loading = true;
  String filter = 'ALL';
  DateTime? lastUpdated;

  @override
  void initState() {
    super.initState();
    fetchSignals();
}

  Future<void> fetchSignals() async {
    try {
      final fetchedSignals = await SignalService.getLatestSignals();
    setState(() {
        signals = fetchedSignals;
        loading = false;
        lastUpdated = DateTime.now();
      });
    } catch (e) {
      setState(() => loading = false);
      logger.e('Exception fetching signals: $e');
    }
  }

  List<Signal> get filteredSignals {
    if (filter == 'BUY') return signals.where((s) => s.type.toUpperCase() == 'BUY').toList();
    if (filter == 'SELL') return signals.where((s) => s.type.toUpperCase() == 'SELL').toList();
    return signals;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Signal Relay',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: AppTheme.background,
        textTheme: const TextTheme(
          bodyLarge: TextStyle(color: AppTheme.textPrimary),
          bodyMedium: TextStyle(color: AppTheme.textPrimary),
          titleMedium: TextStyle(color: AppTheme.textPrimary, fontWeight: FontWeight.w500),
        ),
      ),
      home: Scaffold(
        backgroundColor: AppTheme.background,
        appBar: AppBar(
          title: const Text(
            'Signal Relay',
            style: TextStyle(
              fontSize: 22, 
              fontWeight: FontWeight.w600,
              letterSpacing: -0.5,
            ),
          ),
          backgroundColor: AppTheme.background,
          centerTitle: false,
          elevation: 0,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh, color: AppTheme.primary),
              onPressed: () {
                setState(() => loading = true);
                fetchSignals();
              },
              tooltip: 'Refresh signals',
            ),
            const SizedBox(width: 8),
          ],
        ),
        body: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Row(
                    children: [
                      ChoiceChip(
                        label: const Text('All'),
                        selected: filter == 'ALL',
                        onSelected: (_) => setState(() => filter = 'ALL'),
                        backgroundColor: AppTheme.cardBackground,
                        selectedColor: AppTheme.primary,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        labelStyle: TextStyle(
                          color: filter == 'ALL' 
                              ? Colors.white 
                              : AppTheme.textPrimary,
                          fontWeight: filter == 'ALL' 
                              ? FontWeight.bold 
                              : FontWeight.normal,
                        ),
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('BUY only'),
                        selected: filter == 'BUY',
                        onSelected: (_) => setState(() => filter = 'BUY'),
                        backgroundColor: AppTheme.cardBackground,
                        selectedColor: AppTheme.buyColor,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        labelStyle: TextStyle(
                          color: filter == 'BUY' 
                              ? Colors.white 
                              : AppTheme.textPrimary,
                          fontWeight: filter == 'BUY' 
                              ? FontWeight.bold 
                              : FontWeight.normal,
                        ),
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('SELL only'),
                        selected: filter == 'SELL',
                        onSelected: (_) => setState(() => filter = 'SELL'),
                        backgroundColor: AppTheme.cardBackground,
                        selectedColor: AppTheme.sellColor,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        labelStyle: TextStyle(
                          color: filter == 'SELL' 
                              ? Colors.white 
                              : AppTheme.textPrimary,
                          fontWeight: filter == 'SELL' 
                              ? FontWeight.bold 
                              : FontWeight.normal,
                        ),
      ),
                    ],
                  ),
                  const Spacer(),
                  if (lastUpdated != null)
                    Text(
                      'Last updated: ${lastUpdated!.hour.toString().padLeft(2, '0')}:${lastUpdated!.minute.toString().padLeft(2, '0')}',
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Expanded(
                child: SingleChildScrollView(
                  child: loading
                      ? const Center(
                          child: CircularProgressIndicator(
                            color: AppTheme.primary,
                          ),
                        )
                      : signals.isEmpty
                          ? const Center(
                              child: Text(
                                'No signals found',
                                style: TextStyle(
                                  color: AppTheme.textSecondary,
                                  fontSize: 16,
                                ),
                              ),
                            )
                          : Card(
                              color: AppTheme.cardBackground,
                              elevation: 4,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: ConstrainedBox(
                                constraints: BoxConstraints(minWidth: MediaQuery.of(context).size.width - 32),
                                child: SingleChildScrollView(
                                  scrollDirection: Axis.horizontal,
                                  child: DataTable(
                                    headingTextStyle: const TextStyle(
                                      color: AppTheme.textPrimary,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 15,
                                    ),
                                    dataTextStyle: const TextStyle(
                                      color: AppTheme.textPrimary,
                                      fontSize: 14,
                                      fontFamily: 'monospace',
                                    ),
                                    columnSpacing: 24,
                                    horizontalMargin: 16,
                                    dividerThickness: 0.5,
                                    columns: const [
                                      DataColumn(label: Text('Symbol')),
                                      DataColumn(label: Text('Action')),
                                      DataColumn(label: Text('Pattern')),
                                      DataColumn(label: Text('Entry')),
                                      DataColumn(label: Text('SL')),
                                      DataColumn(label: Text('TP')),
                                      DataColumn(label: Text('Data Type')),
                                      DataColumn(label: Text('Timestamp')),
                                    ],
                                    rows: filteredSignals
                                        .map(
                                          (s) => DataRow(
                                            cells: [
                                              DataCell(Text(s.symbol)),
                                              DataCell(Row(
                                                mainAxisSize: MainAxisSize.min,
                                                children: [
                                                  Icon(
                                                    s.signalIcon,
                                                    color: s.signalColor,
                                                    size: 16,
                                                  ),
                                                  const SizedBox(width: 4),
                                                  Text(
                                                    s.type,
                                                    style: TextStyle(
                                                      color: s.signalColor,
                                                      fontWeight: FontWeight.bold,
                                                    ),
                                                  ),
                                                ],
                                              )),
                                              DataCell(
                                                Row(
                                                  mainAxisSize: MainAxisSize.min,
                                                  children: [
                                                    Text(s.patternType),
                                                    const SizedBox(width: 4),
                                                    if (s.patternStrength > 0)
            Text(
                                                        '(${s.patternStrength}%)',
                                                        style: const TextStyle(
                                                          color: AppTheme.textSecondary,
                                                          fontSize: 12,
                                                        ),
            ),
          ],
        ),
      ),
                                              DataCell(Text(s.entryPrice?.toStringAsFixed(2) ?? '-')),
                                              DataCell(Text(s.stopLoss?.toStringAsFixed(2) ?? '-')),
                                              DataCell(Text(s.takeProfit?.toStringAsFixed(2) ?? '-')),
                                              DataCell(
                                                Container(
                                                  padding: const EdgeInsets.symmetric(
                                                    horizontal: 8,
                                                    vertical: 2,
                                                  ),
                                                  decoration: BoxDecoration(
                                                    color: s.typeOfData == 'LIVE'
                                                        ? Colors.blue.withAlpha(51)
                                                        : Colors.orange.withAlpha(51),
                                                    borderRadius: BorderRadius.circular(4),
                                                  ),
                                                  child: Text(
                                                    s.typeOfData,
                                                    style: TextStyle(
                                                      color: s.typeOfData == 'LIVE'
                                                          ? Colors.blue 
                                                          : Colors.orange,
                                                      fontSize: 12,
                                                      fontWeight: FontWeight.bold,
                                                    ),
                                                  ),
                                                ),
                                              ),
                                              DataCell(Text(s.formattedTimestamp)),
                                            ],
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ),
                              ),
                            ),
                ),
              ),
              const SizedBox(height: 16),
              Center(
                child: Text(
                  '© 2025 Giorgos Ampavis. All rights reserved.',
                  style: TextStyle(
                    color: AppTheme.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
