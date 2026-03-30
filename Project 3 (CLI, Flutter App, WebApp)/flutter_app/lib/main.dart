import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:device_preview/device_preview.dart';

import 'widgets/glass_widgets.dart';
import 'screens/splash_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  
  runApp(
    DevicePreview(
      enabled: kDebugMode,
      defaultDevice: Devices.android.samsungGalaxyNote20Ultra,
      builder: (context) => const AuditApp(),
    ),
  );
}

class AuditApp extends StatelessWidget {
  const AuditApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      locale: DevicePreview.locale(context),
      builder: DevicePreview.appBuilder,
      debugShowCheckedModeBanner: false,
      title: 'NSU Degree Audit',
      theme: buildAppTheme(),
      home: const SplashScreen(),
    );
  }
}
