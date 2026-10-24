package org.aief.personalautomator

import android.graphics.Bitmap
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
        ActivityScenario.launch(CaptureActivity::class.java).use { scenario ->
            scenario.recreate()
            instrumentation.waitForIdleSync()
            assertCleared()
        }
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
}
