import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_app/models/health_model.dart';

/// **Bug Condition Exploration Test for Health Screen Data Parsing**
/// 
/// **Validates: Requirements 1.1, 1.2, 1.3, 4.1, 4.2, 4.3**
/// 
/// This test encodes the EXPECTED behavior for parsing the nested API response
/// from /health/realtime endpoint. It tests that HealthModel.fromJson() correctly
/// parses the nested 'layers' structure with backend, database sub-objects.
/// 
/// **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists.
/// When run on unfixed code, this test will surface counterexamples demonstrating:
/// - Backend status is null/unknown (not extracted from layers.backend.status)
/// - Database status is null/unknown (not extracted from layers.database.status)
/// - Uptime is 0 or incorrect (not extracted from uptime.seconds)
/// 
/// **Property 1: Bug Condition - Health Screen Nested Layers Parsing**
/// 
/// For any API response from /health/realtime that contains a 'layers' object
/// with nested infrastructure data, the HealthModel SHALL correctly parse the
/// nested structure and extract all layer statuses and metrics.

void main() {
  group('Bug Condition Exploration: Health Screen Nested Layers Parsing', () {
    test('Property 1: HealthModel correctly parses nested layers structure from actual API response', () {
      // This is the ACTUAL nested structure returned by /health/realtime endpoint
      final apiResponse = {
        'status': 'healthy',
        'uptime': {
          'seconds': 12345,
          'formatted': '3h 25m 45s',
        },
        'layers': {
          'backend': {
            'status': 'operational',
            'uptime_seconds': 12345,
            'memory_mb': 128,
            'latency_ms': 45,
          },
          'database': {
            'status': 'connected',
            'latency_ms': 23,
            'provider': 'Supabase',
          },
        },
        'metrics': {
          'user_requests': 1234,
          'health_checks': 5678,
          'errors': 2,
        },
      };

      // Parse the response using HealthModel.fromJson()
      final healthModel = HealthModel.fromJson(apiResponse);

      // EXPECTED BEHAVIOR: Backend status should be extracted from layers.backend.status
      // UNFIXED CODE BEHAVIOR: Will be 'unknown' because it looks for json['backend']
      expect(
        healthModel.backend.status,
        isNot('unknown'),
        reason: 'Backend status should be extracted from layers.backend.status, not json["backend"]',
      );
      
      expect(
        healthModel.backend.status,
        equals('operational'),
        reason: 'Backend status should match the value in layers.backend.status',
      );

      // EXPECTED BEHAVIOR: Database status should be extracted from layers.database.status
      // UNFIXED CODE BEHAVIOR: Will be 'unknown' because it looks for json['database']
      expect(
        healthModel.database.status,
        isNot('unknown'),
        reason: 'Database status should be extracted from layers.database.status, not json["database"]',
      );
      
      expect(
        healthModel.database.status,
        equals('connected'),
        reason: 'Database status should match the value in layers.database.status',
      );

      // EXPECTED BEHAVIOR: Uptime should be extracted from uptime.seconds
      // UNFIXED CODE BEHAVIOR: Will be 0 because it looks for json['uptime_seconds']
      expect(
        healthModel.uptimeSeconds,
        greaterThan(0),
        reason: 'Uptime should be extracted from uptime.seconds, not uptime_seconds',
      );
      
      expect(
        healthModel.uptimeSeconds,
        equals(12345),
        reason: 'Uptime should match the value in uptime.seconds',
      );

      // EXPECTED BEHAVIOR: Backend latency should be extracted from layers.backend.latency_ms
      expect(
        healthModel.backend.latencyMs,
        equals(45),
        reason: 'Backend latency should be extracted from layers.backend.latency_ms',
      );

      // EXPECTED BEHAVIOR: Database latency should be extracted from layers.database.latency_ms
      expect(
        healthModel.database.latencyMs,
        equals(23),
        reason: 'Database latency should be extracted from layers.database.latency_ms',
      );
    });

    test('Property 1: HealthModel gracefully handles missing OCR data in layers', () {
      // API response with layers but no OCR data
      final apiResponse = {
        'status': 'healthy',
        'uptime': {
          'seconds': 5000,
          'formatted': '1h 23m 20s',
        },
        'layers': {
          'backend': {
            'status': 'operational',
            'latency_ms': 50,
          },
          'database': {
            'status': 'connected',
            'latency_ms': 30,
          },
          // Note: No 'ocr' or 'ocr_engine' field
        },
      };

      final healthModel = HealthModel.fromJson(apiResponse);

      // EXPECTED BEHAVIOR: OCR status should gracefully default to 'unknown'
      expect(
        healthModel.ocr.status,
        equals('unknown'),
        reason: 'OCR status should gracefully handle missing data',
      );

      // But backend and database should still be parsed correctly
      expect(healthModel.backend.status, equals('operational'));
      expect(healthModel.database.status, equals('connected'));
      expect(healthModel.uptimeSeconds, equals(5000));
    });

    test('Property 1: HealthModel handles uptime counter correctly between fetches', () {
      // First API response
      final firstResponse = {
        'status': 'healthy',
        'uptime': {
          'seconds': 1000,
          'formatted': '16m 40s',
        },
        'layers': {
          'backend': {'status': 'operational', 'latency_ms': 40},
          'database': {'status': 'connected', 'latency_ms': 25},
        },
      };

      // Second API response (3 seconds later)
      final secondResponse = {
        'status': 'healthy',
        'uptime': {
          'seconds': 1003,
          'formatted': '16m 43s',
        },
        'layers': {
          'backend': {'status': 'operational', 'latency_ms': 42},
          'database': {'status': 'connected', 'latency_ms': 27},
        },
      };

      final firstModel = HealthModel.fromJson(firstResponse);
      final secondModel = HealthModel.fromJson(secondResponse);

      // EXPECTED BEHAVIOR: Uptime should increment between fetches
      // UNFIXED CODE BEHAVIOR: Both will be 0 (resets every fetch)
      expect(
        firstModel.uptimeSeconds,
        greaterThan(0),
        reason: 'First uptime should be greater than 0',
      );

      expect(
        secondModel.uptimeSeconds,
        greaterThan(firstModel.uptimeSeconds),
        reason: 'Uptime should increment between fetches, not reset to 0',
      );

      expect(
        secondModel.uptimeSeconds - firstModel.uptimeSeconds,
        equals(3),
        reason: 'Uptime should increase by 3 seconds between fetches',
      );
    });

    test('Property 1: HealthModel handles different field name variations in LayerHealth', () {
      // API response with field name variations
      final apiResponse = {
        'status': 'healthy',
        'uptime': {
          'seconds': 8000,
        },
        'layers': {
          'backend': {
            'status': 'operational',
            'latency': 55, // Note: 'latency' instead of 'latency_ms'
            'note': 'All systems operational', // Note: 'note' instead of 'message'
          },
          'database': {
            'status': 'connected',
            'latency_ms': 28,
            'message': 'Database connection stable',
          },
        },
      };

      final healthModel = HealthModel.fromJson(apiResponse);

      // EXPECTED BEHAVIOR: Should handle both 'latency' and 'latency_ms'
      expect(
        healthModel.backend.latencyMs,
        equals(55),
        reason: 'Should extract latency from "latency" field when "latency_ms" is not present',
      );

      expect(
        healthModel.database.latencyMs,
        equals(28),
        reason: 'Should extract latency from "latency_ms" field',
      );

      // EXPECTED BEHAVIOR: Should handle both 'message' and 'note'
      expect(
        healthModel.backend.message,
        equals('All systems operational'),
        reason: 'Should extract message from "note" field when "message" is not present',
      );

      expect(
        healthModel.database.message,
        equals('Database connection stable'),
        reason: 'Should extract message from "message" field',
      );
    });

    test('Property 1: HealthModel provides backward compatibility with flat structure', () {
      // Old flat structure (for backward compatibility)
      final flatResponse = {
        'status': 'healthy',
        'uptime_seconds': 3000,
        'backend': {
          'status': 'up',
          'latency_ms': 60,
        },
        'database': {
          'status': 'up',
          'latency_ms': 35,
        },
        'ocr': {
          'status': 'up',
          'latency_ms': 100,
        },
      };

      final healthModel = HealthModel.fromJson(flatResponse);

      // EXPECTED BEHAVIOR: Should still work with flat structure for backward compatibility
      expect(healthModel.backend.status, equals('up'));
      expect(healthModel.database.status, equals('up'));
      expect(healthModel.ocr.status, equals('up'));
      expect(healthModel.uptimeSeconds, equals(3000));
    });
  });
}
