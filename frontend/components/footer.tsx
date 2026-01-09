import Logo from "./logo";

function Footer() {
  return (
    <footer className="text-start py-8 text-sm w-full bg-linear-to-br from-gray-500 to-gray-400 px-10 text-secondary">
      <div className="flex justify-between items-center max-w-[1200px] mx-auto">
        <div className="flex gap-1 items-center justify-start">
          <Logo size="sm" logoText={["Flower", "head"]} icon="flower" />
          <span>&copy; {new Date().getFullYear()}</span>
        </div>
        <div className="flex items-center justify-center gap-1 group">
          <span className=" group-hover:text-muted-foreground transition-all duration-300">
            Get in Touch &#x2192;
          </span>
          <div className="hover:-translate-y-2 transition-all duration-500 h-full">
            <a
              href="mailto:flowerhead.dev@gmail.com?subject=I%20have%20a%20project%20I'd%20like%20help%20with"
              className=" hover:text-gray-400 transition-al duration-300  flex justify-center items-center gap-2 "
            >
              <Logo size="sm" logoText={["Flower", "head"]} icon="flower" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
