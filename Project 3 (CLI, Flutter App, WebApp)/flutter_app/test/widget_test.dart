import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_app/main.dart';

void main() {
  testWidgets('renders the premium landing screen', (tester) async {
    await tester.pumpWidget(const AuditApp());

    expect(find.text('North South University'), findsOneWidget);
    expect(find.text('Pick Transcript'), findsOneWidget);
  });
}
