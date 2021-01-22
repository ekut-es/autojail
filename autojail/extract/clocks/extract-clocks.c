#include <linux/clk-provider.h>
#include <linux/clk.h>
#include <linux/clk/clk-conf.h>
#include <linux/debugfs.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_clk.h>

#define DEVS 30
#define REGS 32

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Christoph Gerum<christoph.gerum @uni - tuebingen.de>");
MODULE_DESCRIPTION(
    "A Linux Kernel module to extract current clock frequencies of device "
    "clock inputs and relate them to device tree paths");
MODULE_VERSION("0.1");

static int of_clk_frequency_fill(struct device_node *np, int *frequencies,
                                 int max_clocks) {
  struct clk *clk;
  struct of_phandle_args clkspec;
  struct property *prop;
  const char *clk_name;
  const __be32 *vp;
  u32 pv;
  int rc, count, index;
  int num_clocks;

  for (num_clocks = 0; num_clocks < max_clocks; num_clocks++) {

    rc = of_parse_phandle_with_args(np, "clocks", "#clock-cells", num_clocks,
                                    &clkspec);
    if (rc)
      break;

    index = clkspec.args_count ? clkspec.args[0] : 0;
    count = 0;

    /* if there is an indices property, use it to transfer the index
     * specified into an array offset for the clock-output-names property.
     */
    of_property_for_each_u32(clkspec.np, "clock-indices", prop, vp, pv) {
      if (index == pv) {
        index = count;
        break;
      }
      count++;
    }
    /* We went off the end of 'clock-indices' without finding it */
    if (prop && !vp) {
      of_node_put(clkspec.np);
      break;
    }

    struct clk *clk = of_clk_get_from_provider(&clkspec);
    if (clk == ERR_PTR(-ENOENT)) {
      of_node_put(clkspec.np);
      break;
    } else {
      printk("CLK: %p", clk);

      int clk_rate = clk_get_rate(clk);
      frequencies[num_clocks] = clk_rate;
      frequencies[num_clocks] = -1;
      clk_put(clk);
    }
    of_node_put(clkspec.np);
  }
  return num_clocks;
}

static int extract_clocks_show(struct seq_file *s, void *data) {
  const int max_clocks = 64;
  const int buffer_length = 1024;
  struct device_node *dev_node = NULL;
  int num_parents;
  const char *clock_parents[max_clocks];
  int num_clocks;
  int frequencies[max_clocks];
  char buffer[buffer_length];
  int num_items;
  int first = 1;
  int i;

  seq_puts(s, "{\n");

  num_clocks = 0;
  num_parents = 0;

  for (dev_node = of_find_all_nodes(NULL); dev_node != NULL;
       dev_node = of_find_all_nodes(dev_node)) {
    const char *node_name = dev_node->name;
    if (dev_node->full_name) {
      node_name = dev_node->full_name;
    }

    printk("Extracting from node %s\n", node_name);

    num_parents = of_clk_parent_fill(dev_node, clock_parents, max_clocks);
    // num_clocks = of_clk_frequency_fill(dev_node, frequencies, max_clocks);

    num_items = (num_clocks < num_parents) ? num_parents : num_clocks;
    if (num_items > 0) {
      if (!first) {
        seq_puts(s, ",\n");
      }
      first = 0;

      snprintf(buffer, buffer_length, "\"%s\":\n", node_name);
      seq_puts(s, buffer);
      seq_puts(s, "  [\n");
      for (i = 0; i < num_items; i++) {
        seq_puts(s, "    {");
        if (num_parents > i) {
          snprintf(buffer, buffer_length, "\"parent_name\": \"%s\"",
                   clock_parents[i]);
          seq_puts(s, buffer);
          if (num_clocks > i) {
            seq_puts(s, ", ");
          }
        }

        if (num_clocks > i) {
          snprintf(buffer, buffer_length, "\"rate\": %d", frequencies[i]);
          seq_puts(s, buffer);
        }

        if (i < (num_items - 1)) {
          seq_puts(s, "},\n");
        } else {
          seq_puts(s, "}\n");
        }
      }
      seq_puts(s, "  ]");
    }
  }

  /*for (; *lists; lists++) {
    hlist_for_each_entry(c, *lists, child_node) {}
  }*/

  seq_puts(s, "\n}\n");
  return 0;
}

DEFINE_SHOW_ATTRIBUTE(extract_clocks);

struct dentry *autojail_dir, *clocks_file;

static int __init extract_clocks_init(void) {

  autojail_dir = debugfs_create_dir("autojail", NULL);
  if (!autojail_dir)
    return -ENOMEM;

  clocks_file = debugfs_create_file("clocks", 0444, autojail_dir, NULL,
                                    &extract_clocks_fops);
  if (!clocks_file)
    return -ENOMEM;

  return 0;
}

static void __exit extract_clocks_exit(void) {
  printk(KERN_INFO "Removing autojail clock info extraction module \n");
  debugfs_remove_recursive(autojail_dir);
}

module_init(extract_clocks_init);
module_exit(extract_clocks_exit);
