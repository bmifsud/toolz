package org.aief.personalautomator

import android.graphics.Bitmap
import android.content.Intent
import android.view.WindowManager
import androidx.lifecycle.Lifecycle
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.After
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** No accessibility enablement, permission grants, projection tokens or real screen pixels. */
@RunWith(AndroidJUnit4::class)
class CaptureLifecycleTest {
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()

    @After fun cleanup() {
        instrumentation.runOnMainSync { CaptureActivity.invalidate() }
        instrumentation.waitForIdleSync()
    }

    private fun assertCleared() {
        instrumentation.runOnMainSync {
            assertNull(CaptureActivity.current)
            assertNull(CaptureService.active)
        }
    }

    private fun awaitServiceRevocation() {
        // Service delivery crosses the Binder queue; main-thread idleness alone is insufficient.
        val deadline = android.os.SystemClock.uptimeMillis() + 5000
        while (android.os.SystemClock.uptimeMillis() < deadline) {
            var revoked = false
            instrumentation.runOnMainSync { revoked = CaptureActivity.current == null }
            if (revoked) { assertCleared(); return }
            android.os.SystemClock.sleep(25)
        }
        assertCleared()
    }

    @Test fun backgroundClearsActivityOwnership() {
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                assertSame(activity, CaptureActivity.current)
                assertFalse(activity.authorized())
                assertTrue(activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0)
            }
            scenario.moveToState(Lifecycle.State.CREATED)
            assertCleared()
            scenario.moveToState(Lifecycle.State.RESUMED)
            scenario.onActivity { activity -> assertFalse(activity.authorized()) }
        }
        assertCleared()
    }

    @Test fun recreationDoesNotRestoreCaptureOwnership() {
        val scenario = ActivityScenario.launch(CaptureActivity::class.java)
        var original: CaptureActivity? = null
        scenario.onActivity { activity ->
            original = activity
            assertSame(activity, CaptureActivity.current)
            activity.recreate()
        }
        instrumentation.waitForIdleSync()
        runCatching { scenario.close() }
        instrumentation.waitForIdleSync()
        assertCleared()
        original?.let { assertTrue(it.isFinishing || it.isDestroyed) }
    }

    @Test fun explicitInvalidationIsIdempotent() {
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.onActivity {
                CaptureActivity.invalidate()
                CaptureActivity.invalidate()
                assertNull(CaptureActivity.current)
                assertNull(CaptureService.active)
            }
        }
        assertCleared()
    }

    @Test fun unauthorizedSyntheticFrameIsRecycledAndActivityRevoked() {
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                val frame = Bitmap.createBitmap(2, 2, Bitmap.Config.ARGB_8888)
                activity.show(frame)
                assertTrue(frame.isRecycled)
                assertFalse(activity.authorized())
                assertNull(CaptureActivity.current)
                assertNull(CaptureService.active)
            }
        }
        assertCleared()
    }

    @Test fun deniedConsentDiscardsActivity() {
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                // Deliver only a denial; never synthesize a successful OS grant.
                CaptureActivity::class.java.getDeclaredMethod("onActivityResult",
                    Int::class.javaPrimitiveType, Int::class.javaPrimitiveType, Intent::class.java)
                    .apply { isAccessible = true }
                    .invoke(activity, 1, android.app.Activity.RESULT_CANCELED, null)
                assertTrue(activity.isFinishing)
            }
        }
        assertCleared()
    }

    @Test fun unauthorizedServiceStartImmediatelyRevokesActivity() {
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                // No consent Intent, no permission grant and no MediaProjection call.
                activity.startService(Intent(activity, CaptureService::class.java))
            }
            awaitServiceRevocation()
        }
    }

    @Test fun notificationStopCommandRevokesActivityWithoutProjection() {
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                activity.startService(Intent(activity, CaptureService::class.java).setAction("STOP"))
            }
            awaitServiceRevocation()
        }
    }
}
