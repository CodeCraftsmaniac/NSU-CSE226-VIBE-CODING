import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'services/supabase_service.dart';
import 'widgets/glass_widgets.dart';
import 'screens/splash_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    statusBarBrightness: Brightness.dark,
    systemNavigationBarColor: kBackground,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  await storageService.getToken();
  await authService.initialize();

  runApp(
    ChangeNotifierProvider<AuthService>.value(
      value: authService,
      child: const AuditApp(),
    ),
  );
}

class AuditApp extends StatelessWidget {
  const AuditApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'NSU Degree Audit',
      theme: buildAppTheme(),
      home: const SplashScreen(),
    );
  }
}
