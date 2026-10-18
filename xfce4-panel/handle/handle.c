/*
 * Redmond2K grab handle: a panel item that draws nothing but its own CSS
 * background and border, so the theme decides what it looks like (see
 * .redmond2k-handle in theme/Redmond2K/gtk-3.0/gtk-xfce4.css).
 *
 * The stock separator plugin can't be used for this: it paints its line and
 * dots with cairo and never renders CSS.
 */

#include <gtk/gtk.h>
#include <libxfce4panel/libxfce4panel.h>

/* Width used when the theme gives the handle no border or padding, so the
 * item can still be found and dragged around the panel. */
#define FALLBACK_SIZE 8

typedef struct _HandlePluginClass HandlePluginClass;
typedef struct _HandlePlugin HandlePlugin;

struct _HandlePluginClass
{
  XfcePanelPluginClass __parent__;
};

struct _HandlePlugin
{
  XfcePanelPlugin __parent__;
};

XFCE_PANEL_DEFINE_PLUGIN (HandlePlugin, handle_plugin)

static void
handle_plugin_update_size (XfcePanelPlugin *plugin)
{
  GtkStyleContext *ctx = gtk_widget_get_style_context (GTK_WIDGET (plugin));
  GtkStateFlags state = gtk_widget_get_state_flags (GTK_WIDGET (plugin));
  GtkBorder border, padding;
  gint size = xfce_panel_plugin_get_size (plugin);
  gint thickness;

  gtk_style_context_get_border (ctx, state, &border);
  gtk_style_context_get_padding (ctx, state, &padding);

  if (xfce_panel_plugin_get_orientation (plugin) == GTK_ORIENTATION_HORIZONTAL)
    {
      thickness = border.left + border.right + padding.left + padding.right;
      gtk_widget_set_size_request (GTK_WIDGET (plugin),
                                   thickness > 0 ? thickness : FALLBACK_SIZE, size);
    }
  else
    {
      thickness = border.top + border.bottom + padding.top + padding.bottom;
      gtk_widget_set_size_request (GTK_WIDGET (plugin),
                                   size, thickness > 0 ? thickness : FALLBACK_SIZE);
    }
}

static void
handle_plugin_update_orientation (XfcePanelPlugin *plugin)
{
  GtkStyleContext *ctx = gtk_widget_get_style_context (GTK_WIDGET (plugin));
  gboolean horizontal = xfce_panel_plugin_get_orientation (plugin) == GTK_ORIENTATION_HORIZONTAL;

  if (horizontal)
    {
      gtk_style_context_remove_class (ctx, GTK_STYLE_CLASS_VERTICAL);
      gtk_style_context_add_class (ctx, GTK_STYLE_CLASS_HORIZONTAL);
    }
  else
    {
      gtk_style_context_remove_class (ctx, GTK_STYLE_CLASS_HORIZONTAL);
      gtk_style_context_add_class (ctx, GTK_STYLE_CLASS_VERTICAL);
    }

  handle_plugin_update_size (plugin);
}

static gboolean
handle_plugin_draw (GtkWidget *widget,
                    cairo_t *cr)
{
  GtkStyleContext *ctx = gtk_widget_get_style_context (widget);
  gint width = gtk_widget_get_allocated_width (widget);
  gint height = gtk_widget_get_allocated_height (widget);

  gtk_render_background (ctx, cr, 0, 0, width, height);
  gtk_render_frame (ctx, cr, 0, 0, width, height);

  return FALSE;
}

static void
handle_plugin_style_updated (GtkWidget *widget)
{
  GTK_WIDGET_CLASS (handle_plugin_parent_class)->style_updated (widget);

  /* the theme may have changed the border width */
  handle_plugin_update_size (XFCE_PANEL_PLUGIN (widget));
}

static gboolean
handle_plugin_size_changed (XfcePanelPlugin *plugin,
                            gint size)
{
  handle_plugin_update_size (plugin);
  return TRUE;
}

static void
handle_plugin_orientation_changed (XfcePanelPlugin *plugin,
                                   GtkOrientation orientation)
{
  handle_plugin_update_orientation (plugin);
}

static void
handle_plugin_construct (XfcePanelPlugin *plugin)
{
  gtk_style_context_add_class (gtk_widget_get_style_context (GTK_WIDGET (plugin)),
                               "redmond2k-handle");
  handle_plugin_update_orientation (plugin);
  gtk_widget_queue_draw (GTK_WIDGET (plugin));
}

static void
handle_plugin_class_init (HandlePluginClass *klass)
{
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (klass);
  XfcePanelPluginClass *plugin_class = XFCE_PANEL_PLUGIN_CLASS (klass);

  widget_class->draw = handle_plugin_draw;
  widget_class->style_updated = handle_plugin_style_updated;

  plugin_class->construct = handle_plugin_construct;
  plugin_class->size_changed = handle_plugin_size_changed;
  plugin_class->orientation_changed = handle_plugin_orientation_changed;
}

static void
handle_plugin_init (HandlePlugin *plugin)
{
}
